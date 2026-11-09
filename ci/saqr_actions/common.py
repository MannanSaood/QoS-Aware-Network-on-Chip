"""Shared helpers for running the frozen SAQR held-out matrices on GitHub Actions.

Nothing here changes the frozen protocols. The runners' own scripts, binaries and
receipts are shipped byte-exact in bundle.tar.gz (git line-ending conversion
would otherwise change hashed sources) and every job re-verifies them by
recomputing both protocols and comparing them with the frozen protocol files.
"""
import json
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
MESHES = [8, 16, 32]          # k = 4 is complete locally for both stages


def verify_frozen():
    """Recompute both protocols from the files on disk; they must equal the frozen ones."""
    import numpy
    import platform
    assert numpy.__version__ == NUMPY_VERSION, f'numpy {numpy.__version__} != {NUMPY_VERSION}'
    assert platform.python_version().startswith(PYTHON_PREFIX), platform.python_version()
    gp = json.loads((g4.OUT / 'protocol.json').read_text())
    assert g4.protocol() == gp, 'G4 protocol mismatch (binary, sources or receipts differ from the frozen ones)'
    sp = json.loads((sg4.OUT / 'protocol_src.json').read_text())
    assert sg4.protocol() == sp, 'SAQR-SC protocol mismatch'
    return gp, sp


def jobs(gp, sp, meshes=MESHES):
    """Every run of both frozen matrices for the given meshes, grouped by case."""
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
