"""O1TURN extension of G5 (docs/SAQR_SPEC_V2.md §21.7). Fixed before any of its runs.

Question: is the SAQR gain just O1TURN? SAQR's adaptive packets use an O1TURN-style
route set, so two extra routes run on exactly the G5 cases (same seeds 301-305, same
traces, same meshes, weighted mode, same frozen comparator binary):

  o1turn    classic O1TURN (Seo et al., ISCA 2005): every packet takes XY or YX with equal
            probability, XY on VC 0 and YX on VC 1 of its class (route `noc_o1turn_mesh`,
            invariant-checked in the binary). A published comparator.
  saqr_all  ablation: SAQR-SC with the classifier forced on (thresholds 0/0), so every packet
            uses SAQR's soft-O1TURN route set. Shows what the classifier itself contributes.

The G5 matrix itself (scripts/saqr_g5_study.py, its protocol and results) is not modified;
this stage only adds runs. Scoring: scripts/evaluate_saqr_o1t.py (criteria in its docstring).
"""
import saqr_g5_study as g5
from saqr_hot_common import ROOT, sha
import saqr_h_study as hs

O1T_DIR = g5.SAQR_STUDY / 'g5_o1t'
ROUTES = {'o1turn': ['o1turn', {}, 'x'],
          'saqr_all': ['saqr_nogate', dict(hs.SC_ENV, NOC_SAQR_SRC_ON=0, NOC_SAQR_SRC_OFF=0), 'x']}
SOURCES = ['scripts/saqr_o1t_study.py', 'scripts/evaluate_saqr_o1t.py']
make_trace = g5.make_trace


def protocol():
    gp = g5.protocol()
    return dict(stage='saqr_g5_o1turn', seeds=gp['seeds'], meshes=gp['meshes'], modes=gp['modes'], traffic=gp['traffic'],
                cases=gp['cases'], routes=ROUTES, binaries={'x': gp['binaries']['x']},
                binary_sha256={'x': gp['binary_sha256']['x']}, g5_protocol_sha256=sha(g5.G5_DIR / 'protocol.json'),
                source_sha256={s: sha(ROOT / s) for s in SOURCES}, warmup=5000, measurement=20000,
                criteria='scripts/evaluate_saqr_o1t.py (hash in source_sha256)')
