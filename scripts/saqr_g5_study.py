"""Fresh held-out G5 (docs/SAQR_SPEC_V2.md §21). Fixed before any G5 run.

Seeds 301-305 (never used before). Meshes 4, 8, 16, 32. Weighted QoS mode.
5000 warm-up + 20000 measured cycles, frozen router configuration.

Traffic (13): the six frozen G4 cases (uniform, transpose, bursty, hotspot_corner,
hotspot_edge, hotspot_center; frozen generator) plus seven patterns never used to
design or tune any candidate (scripts/traffic_ext.py: bitcomp, bitrev, shuffle,
tornado, neighbor, multiflow, mixed). Load grids: the frozen 9-point grids
(hotspot grid for hotspot cases, the uniform grid for every other pattern).

Routes (10):
  comparators (8): xy, oefixed, dyad, topsis, duato, westfirst (frozen SAQR binary),
                   dbar, footprint (comparator binary, §21; Duato framework, DBAR idealized)
  candidates  (2): saqr_sc (frozen §19, SAQR-SC binary), saqr_h (§20, variant chosen by the
                   SAQR-H tuning pilot's fixed rule, SAQR-H binary)
Scoring: scripts/evaluate_saqr_g5.py (criteria fixed in its docstring).
"""
import json
from saqr_hot_common import ROOT, SAQR_STUDY, SAQR_BINARY, SRC_BINARY, HOT_BINARY, sha, trace as frozen_trace
import traffic_ext
import saqr_h_study as hs
import run_saqr_g4 as g4

X_BINARY = ROOT / '.deps/booksim2_saqr_x/src/booksim'
G5_DIR = SAQR_STUDY / 'g5'
SEEDS = [301, 302, 303, 304, 305]
MESHES = [4, 8, 16, 32]
TRAFFIC = g4.TRAFFIC + traffic_ext.PATTERNS
COMPARATORS = ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint']
CANDIDATES = ['saqr_sc', 'saqr_h']
SOURCES = ['scripts/saqr_g5_study.py', 'scripts/evaluate_saqr_g5.py', 'scripts/traffic_ext.py', 'scripts/qos_common.py',
           'scripts/chr_common.py', 'scripts/saqr_src_common.py', 'scripts/saqr_hot_common.py', 'scripts/saqr_h_study.py',
           'scripts/run_saqr_g4.py', 'scripts/evaluate_saqr_g4.py', 'scripts/setup_saqr_x.py',
           'algorithms/saqr/routing.hpp', 'algorithms/saqr_src/routing.hpp', 'algorithms/saqr_hot/routing.hpp',
           'algorithms/dbar/routing.hpp', 'algorithms/footprint/routing.hpp', 'simulators/booksim_saqr_x/saqr_routes.cpp']


def case(k, traffic, i, seed):
    grid = [.1, .25, .5, .7, .85, 1, 1.15, 1.5, 2] if traffic.startswith('hotspot') else [.02, .05, .1, .2, .3, .4, .6, .8, 1]
    v = grid[i]
    load = float(f'{v/(.2*k*k+.8) if traffic.startswith("hotspot") else v*4/k:.12g}')
    return dict(k=k, traffic=traffic, index=i, load=load, seed=seed, name=f'k{k}_{traffic}_l{i}_s{seed}')


def make_trace(path, c):
    if c['traffic'] in traffic_ext.PATTERNS:
        return traffic_ext.trace(path, c['k'], c['load'], c['seed'], c['traffic'])
    return frozen_trace(path, c['k'], c['load'], c['seed'], c['traffic'])


def binaries():
    return {'saqr': str(SAQR_BINARY.relative_to(ROOT)), 'src': str(SRC_BINARY.relative_to(ROOT)),
            'hot': str(HOT_BINARY.relative_to(ROOT)), 'x': str(X_BINARY.relative_to(ROOT))}


def protocol():
    sel = json.loads((hs.PILOT_DIR / 'selection.json').read_text())['selected']
    assert sel in hs.HOT, 'no SAQR-H variant was selected on tuning data'
    routes = {n: [g4.VARIANTS[n][0], g4.VARIANTS[n][1], 'saqr'] for n in COMPARATORS[:6]}
    routes['dbar'] = ['dbar', {}, 'x']
    routes['footprint'] = ['footprint', {}, 'x']
    routes['saqr_sc'] = ['saqr_nogate', hs.SC_ENV, 'src']
    routes['saqr_h'] = ['saqr_nogate', hs.hot_env(sel), 'hot']
    cases = [case(k, t, i, s) for k in MESHES for t in TRAFFIC for i in range(9) for s in SEEDS]
    return dict(stage='saqr_g5_heldout', seeds=SEEDS, meshes=MESHES, modes=['weighted'], traffic=TRAFFIC, cases=cases,
                routes=routes, comparators=COMPARATORS, candidates=CANDIDATES, selected_variant=sel, binaries=binaries(),
                binary_sha256={b: sha(ROOT / p) for b, p in binaries().items()},
                source_sha256={s: sha(ROOT / s) for s in SOURCES},
                pilot_selection_sha256=sha(hs.PILOT_DIR / 'selection.json'),
                warmup=5000, measurement=20000, criteria='scripts/evaluate_saqr_g5.py (hash in source_sha256)')
