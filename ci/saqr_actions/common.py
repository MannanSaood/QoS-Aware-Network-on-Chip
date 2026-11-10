"""Shared helpers for running frozen SAQR study matrices on GitHub Actions.

Stages (env SAQR_STAGE):
  g4      the G4 + SAQR-SC held-out (seeds 201-205; complete)
  hpilot  SAQR-H tuning pilot (seeds 101-103; scripts/saqr_h_study.py)
  g5      fresh held-out: 8 comparators incl. DBAR/Footprint, saqr_sc and saqr_h, 13 traffic
          patterns (seeds 301-305; scripts/saqr_g5_study.py)
  o1t     G5 extension: classic O1TURN + the saqr_all ablation on the G5 cases
          (scripts/saqr_o1t_study.py)
  cpilot  SAQR-C design pilot on G5 seeds 301-302 (scripts/saqr_c_study.py)

Nothing here changes a frozen protocol. Scripts, binaries and receipts ship
byte-exact in bundle.tar.gz (git line-ending conversion would change hashed
sources) and every job recomputes the stage's protocol and requires it to equal
the frozen protocol file.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

import saqr_src_common  # noqa: E402,F401  (extends the tuning-env whitelist with the SAQR-SC variables)
from chr_common import SAQR_BINARY, sha  # noqa: E402
import run_saqr_g4 as g4  # noqa: E402
import run_saqr_src_g4 as sg4  # noqa: E402
from saqr_src_common import SRC_BINARY  # noqa: E402

NUMPY_VERSION = '1.26.4'      # version that generated every local trace (Ubuntu 24.04 python3-numpy)
PYTHON_PREFIX = '3.12.'
STAGE = os.environ.get('SAQR_STAGE', 'g4')
MESHES = [8, 16, 32]          # g4: k = 4 is complete locally for both stages


def _platform():
    import numpy
    import platform
    assert numpy.__version__ == NUMPY_VERSION, f'numpy {numpy.__version__} != {NUMPY_VERSION}'
    assert platform.python_version().startswith(PYTHON_PREFIX), platform.python_version()


def verify_frozen():
    """Recompute the G4 and SAQR-SC protocols from the files on disk; they must equal the frozen ones."""
    _platform()
    gp = json.loads((g4.OUT / 'protocol.json').read_text())
    assert g4.protocol() == gp, 'G4 protocol mismatch (binary, sources or receipts differ from the frozen ones)'
    sp = json.loads((sg4.OUT / 'protocol_src.json').read_text())
    assert sg4.protocol() == sp, 'SAQR-SC protocol mismatch'
    return gp, sp


def jobs(gp, sp, meshes=MESHES):
    """G4 stage: every run of both frozen matrices for the given meshes, grouped by case."""
    out = []
    for c in gp['cases']:
        if c['k'] not in meshes:
            continue
        js = []
        for mode in gp['modes']:
            for name, (alg, env) in g4.VARIANTS.items():
                js.append(dict(stage='g4', mode=mode, name=name, alg=alg, env=env, binary=str(SAQR_BINARY.relative_to(ROOT)),
                               dir=str((g4.OUT / 'cases' / c['name'] / f'{mode}_{name}').relative_to(ROOT))))
            js.append(dict(stage='src', mode=mode, name='saqr_sc', alg=sp['algorithm'], env=sp['env'], binary=str(SRC_BINARY.relative_to(ROOT)),
                           dir=str((sg4.OUT / 'cases' / c['name'] / f'{mode}_saqr_sc').relative_to(ROOT))))
        out.append((c, js))
    return out


def demand_path(c):
    return g4.OUT / 'cases' / c['name'] / 'demand.txt'


class Stage:
    """Uniform interface used by lane.py and status.py."""

    def __init__(self, name=STAGE):
        self.name = name
        if name == 'g4':
            self.gp, self.sp = verify_frozen()
        elif name == 'hpilot':
            verify_frozen()                      # the bundle's frozen G4/SAQR-SC files must still be intact
            import saqr_h_study as hs
            d, want = hs.PILOT_DIR, hs.pilot_protocol()
            have = json.loads((d / 'protocol.json').read_text())
            assert want == have, f'{name} protocol mismatch (binary, sources or design differ from the frozen ones)'
            self.dir, self.proto = d, have
        elif name in ('g5', 'o1t', 'cpilot'):
            verify_frozen()
            import saqr_g5_study as gs
            self.gs = gs
            if name == 'cpilot':
                import saqr_c_study as cs
                d, want = cs.PILOT_DIR, cs.pilot_protocol()
            elif name == 'o1t':
                import saqr_o1t_study as os_
                d, want = os_.O1T_DIR, os_.protocol()
            else:
                d, want = gs.G5_DIR, gs.protocol()
            have = json.loads((d / 'protocol.json').read_text())
            assert want == have, f'{name} protocol mismatch (binary, sources or design differ from the frozen ones)'
            self.dir, self.proto = d, have

    def done(self):
        if self.name == 'g4':
            return json.loads((ROOT / 'ci_bundle' / 'done.json').read_text())
        return {}

    def meshes(self):
        return MESHES if self.name == 'g4' else self.proto['meshes']

    def jobs(self, meshes=None):
        meshes = meshes or self.meshes()
        if self.name == 'g4':
            return jobs(self.gp, self.sp, meshes)
        out = []
        for c in self.proto['cases']:
            if c['k'] not in meshes:
                continue
            js = [dict(stage=r, mode=mode, name=r, alg=alg, env=env, binary=self.proto['binaries'][b],
                       dir=str((self.dir / 'cases' / c['name'] / f'{mode}_{r}').relative_to(ROOT)))
                  for mode in self.proto['modes'] for r, (alg, env, b) in self.proto['routes'].items()]
            out.append((c, js))
        return out

    def make_trace(self, path, c):
        if self.name in ('g5', 'o1t', 'cpilot'):
            return self.gs.make_trace(path, c)
        from chr_common import trace
        return trace(path, c['k'], c['load'], c['seed'], c['traffic'])

    def demand(self, c):
        return demand_path(c) if self.name == 'g4' else self.dir / 'cases' / c['name'] / 'demand.txt'
