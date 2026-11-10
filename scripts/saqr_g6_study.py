"""Fresh held-out G6 (docs/SAQR_SPEC_V2.md §22). Defined before the SAQR-C pilot ran.

Seeds 401-405 (never used before). Meshes 4, 8, 16, 32. Weighted QoS mode, 5000 warm-up +
20000 measured cycles, frozen router configuration.
Traffic (15): the 13 G5 patterns (used for design from §21.6 on; the seeds are fresh) plus two
patterns never used for design, tuning or selection (scripts/traffic_g6.py: butterfly, randperm).
Load grids: the frozen 9-point grids (hotspot grid for hotspot cases, uniform grid otherwise).
Routes (11):
  comparators (9): xy, oefixed, dyad, topsis, duato, westfirst, dbar, footprint, o1turn
                   (all on the comparator binary, which reproduces the frozen binaries bit for bit)
  candidates  (2): saqr_c (the variant chosen by the SAQR-C pilot's fixed rule, SAQR-C binary),
                   saqr_h (h13, unchanged, for reference)
Scoring: scripts/evaluate_saqr_g6.py (criteria fixed in its docstring).
"""
import json
import saqr_col_common  # noqa: F401
from saqr_col_common import ROOT, SAQR_STUDY, COL_BINARY, sha
import saqr_g5_study as g5
import saqr_c_study as cs
import saqr_h_study as hs
import traffic_g6

G6_DIR = SAQR_STUDY / 'g6'
SEEDS = [401, 402, 403, 404, 405]
MESHES = [4, 8, 16, 32]
TRAFFIC = g5.TRAFFIC + traffic_g6.PATTERNS
COMPARATORS = ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint', 'o1turn']
CANDIDATES = ['saqr_c', 'saqr_h']
SOURCES = ['scripts/saqr_g6_study.py', 'scripts/evaluate_saqr_g6.py', 'scripts/traffic_g6.py', 'scripts/traffic_ext.py',
           'scripts/saqr_c_study.py', 'scripts/saqr_col_common.py', 'scripts/saqr_g5_study.py', 'scripts/evaluate_saqr_g4.py',
           'algorithms/saqr_col/routing.hpp', 'simulators/booksim_saqr_c/saqr_routes.cpp', 'simulators/booksim_saqr_x/saqr_routes.cpp']


def case(k, traffic, i, seed):
    return g5.case(k, traffic, i, seed)


def make_trace(path, c):
    if c['traffic'] in traffic_g6.PATTERNS:
        return traffic_g6.trace(path, c['k'], c['load'], c['seed'], c['traffic'])
    return g5.make_trace(path, c)


def protocol():
    sel = json.loads((cs.PILOT_DIR / 'selection.json').read_text())['selected']
    assert sel in cs.VARIANTS, 'no SAQR-C variant was selected on design data'
    import run_saqr_g4 as g4
    routes = {n: [g4.VARIANTS[n][0], g4.VARIANTS[n][1], 'x'] for n in COMPARATORS[:6]}
    routes.update(dbar=['dbar', {}, 'x'], footprint=['footprint', {}, 'x'], o1turn=['o1turn', {}, 'x'])
    routes['saqr_c'] = ['saqr_nogate', cs.col_env(sel), 'c']
    routes['saqr_h'] = ['saqr_nogate', hs.hot_env('h13'), 'x']
    binaries = {'x': str(g5.X_BINARY.relative_to(ROOT)), 'c': str(COL_BINARY.relative_to(ROOT))}
    cases = [case(k, t, i, s) for k in MESHES for t in TRAFFIC for i in range(9) for s in SEEDS]
    return dict(stage='saqr_g6_heldout', seeds=SEEDS, meshes=MESHES, modes=['weighted'], traffic=TRAFFIC, cases=cases,
                routes=routes, comparators=COMPARATORS, candidates=CANDIDATES, selected_variant=sel, binaries=binaries,
                binary_sha256={b: sha(ROOT / p) for b, p in binaries.items()}, source_sha256={s: sha(ROOT / s) for s in SOURCES},
                pilot_selection_sha256=sha(cs.PILOT_DIR / 'selection.json'), warmup=5000, measurement=20000,
                criteria='scripts/evaluate_saqr_g6.py (hash in source_sha256)')
