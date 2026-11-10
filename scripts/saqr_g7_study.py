"""Fresh held-out G7 for SAQR-CT (docs/SAQR_SPEC_V2.md §23). Defined before the SAQR-CT pilot ran.

Seeds 501-505 (never used before). Meshes 4, 8, 16, 32. Weighted QoS mode, 5000 warm-up +
20000 measured cycles, frozen router configuration.
Traffic (17): the 15 G6 patterns (used for design; seeds fresh) plus two patterns never used for
design, tuning or selection (scripts/traffic_g7.py: antitranspose, unshuffle).
Routes (11):
  comparators (9): xy, oefixed, dyad, topsis, duato, westfirst, dbar, footprint, o1turn (comparator binary)
  candidates  (2): saqr_ct (variant chosen by the SAQR-CT pilot's fixed rule, SAQR-CT binary),
                   saqr_c (c25, SAQR-C binary, for reference)
Run only if the pilot selects a SAQR-CT variant. Scoring: scripts/evaluate_saqr_g7.py.
"""
import json
import saqr_ct_common  # noqa: F401
from saqr_ct_common import ROOT, SAQR_STUDY, CT_BINARY, COL_BINARY, sha
import saqr_g5_study as g5
import saqr_g6_study as g6
import saqr_c_study as cs
import saqr_ct_study as ts
import traffic_g7

G7_DIR = SAQR_STUDY / 'g7'
SEEDS = [501, 502, 503, 504, 505]
MESHES = [4, 8, 16, 32]
TRAFFIC = g6.TRAFFIC + traffic_g7.PATTERNS
COMPARATORS = g6.COMPARATORS
CANDIDATES = ['saqr_ct', 'saqr_c']
SOURCES = ['scripts/saqr_g7_study.py', 'scripts/evaluate_saqr_g7.py', 'scripts/traffic_g7.py', 'scripts/traffic_g6.py',
           'scripts/traffic_ext.py', 'scripts/saqr_ct_study.py', 'scripts/saqr_ct_common.py', 'scripts/saqr_c_study.py',
           'scripts/evaluate_saqr_g4.py', 'algorithms/saqr_ct/routing.hpp', 'simulators/booksim_saqr_ct/saqr_routes.cpp']


def make_trace(path, c):
    if c['traffic'] in traffic_g7.PATTERNS:
        return traffic_g7.trace(path, c['k'], c['load'], c['seed'], c['traffic'])
    return g6.make_trace(path, c)


def protocol():
    sel = json.loads((ts.PILOT_DIR / 'selection.json').read_text())['selected']
    assert sel in ts.VARIANTS, 'the SAQR-CT pilot did not select a SAQR-CT variant; G7 is not run'
    import run_saqr_g4 as g4
    routes = {n: [g4.VARIANTS[n][0], g4.VARIANTS[n][1], 'x'] for n in COMPARATORS[:6]}
    routes.update(dbar=['dbar', {}, 'x'], footprint=['footprint', {}, 'x'], o1turn=['o1turn', {}, 'x'])
    routes['saqr_ct'] = ['saqr_nogate', ts.ct_env(sel), 'ct']
    routes['saqr_c'] = ['saqr_nogate', cs.col_env('c25'), 'c']
    binaries = {'x': str(g5.X_BINARY.relative_to(ROOT)), 'c': str(COL_BINARY.relative_to(ROOT)), 'ct': str(CT_BINARY.relative_to(ROOT))}
    cases = [g5.case(k, t, i, s) for k in MESHES for t in TRAFFIC for i in range(9) for s in SEEDS]
    return dict(stage='saqr_g7_heldout', seeds=SEEDS, meshes=MESHES, modes=['weighted'], traffic=TRAFFIC, cases=cases,
                routes=routes, comparators=COMPARATORS, candidates=CANDIDATES, selected_variant=sel, binaries=binaries,
                binary_sha256={b: sha(ROOT / p) for b, p in binaries.items()}, source_sha256={s: sha(ROOT / s) for s in SOURCES},
                pilot_selection_sha256=sha(ts.PILOT_DIR / 'selection.json'), warmup=5000, measurement=20000,
                criteria='scripts/evaluate_saqr_g7.py (hash in source_sha256)')
