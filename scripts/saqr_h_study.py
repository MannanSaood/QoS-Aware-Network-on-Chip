"""SAQR-H study definition (docs/SAQR_SPEC_V2.md §20): tuning pilot and fresh held-out (G5).

Everything below is fixed before any SAQR-H simulation is run.

Tuning pilot (seeds 101-103, never held out):
  meshes 8 and 16; all six traffic cases; loads (frozen grid indices)
    uniform, bursty: 4..8   transpose: 6, 8   hotspot_corner/edge/center: 3..7
  weighted mode; routes: the six comparators (SAQR binary), saqr_sc (SAQR-SC binary,
  frozen §19 settings) and the SAQR-H variants (SAQR-H binary):
    h11   (default)  on .11  off .08  floor .05  init .10  shift 4   (x/4096: 451/328/205/410)
    h13              on .13  off .10  floor .05  init .11  shift 4   (532/410/205/451)
    h11s5            on .11  off .08  floor .05  init .10  shift 5
    h_off            tracker disabled: must equal saqr_sc bit for bit (equivalence check, not a candidate)
  Selection rule: eligible = variants whose weighted throughput paired lower bound vs XY
  (3 seeds, t = 4.303) is > -3 % at every uniform and bursty load at both meshes.
  Among eligible, fewest hotspot points (3 hotspot cases x 5 loads x 2 meshes) whose
  throughput lower bound vs the best comparator (highest mean among the six) is <= -3 %;
  tie -> highest mean hotspot throughput; within 0.5 % of the best -> h11.

Fresh held-out G5 (seeds 301-305, never used before):
  the frozen G4 matrix design (meshes 4/8/16/32, six traffic cases, frozen 9-point load
  grids, both modes, 5000 + 20000 cycles) with routes: the six comparators, saqr_sc and
  saqr_h (the selected variant). Scored with the unchanged scripts/evaluate_saqr_g4.py
  (candidates saqr_sc and saqr_h; same pre-registered C1-C6 criteria and margins).
"""
import json
import math
from saqr_hot_common import ROOT, SAQR_STUDY, SAQR_BINARY, SRC_BINARY, HOT_BINARY, HOT_STUDY, sha
import run_saqr_g4 as g4

SC_ENV = {'NOC_SAQR_O1TURN_MASK': 3, 'NOC_SAQR_SRC_ON': 128, 'NOC_SAQR_SRC_OFF': 64}   # frozen §19 (sc_128_64)
HOT = {'h11': dict(on=451, off=328, floor=205, init=410, shift=4),
       'h13': dict(on=532, off=410, floor=205, init=451, shift=4),
       'h11s5': dict(on=451, off=328, floor=205, init=410, shift=5)}
CANDIDATE_VARIANTS = list(HOT)
COMPARATORS = ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst']
PILOT_SEEDS = [101, 102, 103]
PILOT_MESHES = [8, 16]
PILOT_INDICES = {'uniform': [4, 5, 6, 7, 8], 'bursty': [4, 5, 6, 7, 8], 'transpose': [6, 8],
                 'hotspot_corner': [3, 4, 5, 6, 7], 'hotspot_edge': [3, 4, 5, 6, 7], 'hotspot_center': [3, 4, 5, 6, 7]}
G5_SEEDS = [301, 302, 303, 304, 305]
SOURCES = ['algorithms/saqr_hot/routing.hpp', 'algorithms/saqr_src/routing.hpp', 'algorithms/saqr/routing.hpp',
           'simulators/booksim_saqr_hot/saqr_routes.cpp', 'scripts/setup_saqr_hot.py', 'scripts/saqr_hot_common.py',
           'scripts/saqr_src_common.py', 'scripts/chr_common.py', 'scripts/qos_common.py', 'scripts/saqr_h_study.py',
           'scripts/run_saqr_g4.py', 'scripts/evaluate_saqr_g4.py', 'tests/saqr_hot_test.cpp']
PILOT_DIR = HOT_STUDY / 'pilot'
G5_DIR = HOT_STUDY / 'g5'


def hot_env(v):
    h = HOT[v]
    return {**SC_ENV, 'NOC_SAQR_HOT_ON': h['on'], 'NOC_SAQR_HOT_OFF': h['off'], 'NOC_SAQR_HOT_FLOOR': h['floor'],
            'NOC_SAQR_HOT_INIT': h['init'], 'NOC_SAQR_HOT_SHIFT': h['shift']}


def case(k, traffic, i, seed):
    grid = [.1, .25, .5, .7, .85, 1, 1.15, 1.5, 2] if traffic.startswith('hotspot') else [.02, .05, .1, .2, .3, .4, .6, .8, 1]
    v = grid[i]
    load = float(f'{v/(.2*k*k+.8) if traffic.startswith("hotspot") else v*4/k:.12g}')
    return dict(k=k, traffic=traffic, index=i, load=load, seed=seed, name=f'k{k}_{traffic}_l{i}_s{seed}')


def pilot_routes():
    r = {n: [g4.VARIANTS[n][0], g4.VARIANTS[n][1], 'saqr'] for n in COMPARATORS}
    r['saqr_sc'] = ['saqr_nogate', SC_ENV, 'src']
    for v in HOT:
        r[v] = ['saqr_nogate', hot_env(v), 'hot']
    r['h_off'] = ['saqr_nogate', SC_ENV, 'hot']
    return r


def binaries():
    return {'saqr': str(SAQR_BINARY.relative_to(ROOT)), 'src': str(SRC_BINARY.relative_to(ROOT)), 'hot': str(HOT_BINARY.relative_to(ROOT))}


def pilot_protocol():
    cases = [case(k, t, i, s) for k in PILOT_MESHES for t in PILOT_INDICES for i in PILOT_INDICES[t] for s in PILOT_SEEDS]
    return dict(stage='saqr_h_pilot', seeds=PILOT_SEEDS, meshes=PILOT_MESHES, modes=['weighted'], cases=cases,
                routes=pilot_routes(), binaries=binaries(),
                binary_sha256={b: sha(ROOT / p) for b, p in binaries().items()},
                source_sha256={s: sha(ROOT / s) for s in SOURCES})


def g5_protocol():
    sel = json.loads((PILOT_DIR / 'selection.json').read_text())['selected']
    assert sel in HOT, 'no SAQR-H variant was selected on tuning data'
    routes = {n: [g4.VARIANTS[n][0], g4.VARIANTS[n][1], 'saqr'] for n in COMPARATORS}
    routes['saqr_sc'] = ['saqr_nogate', SC_ENV, 'src']
    routes['saqr_h'] = ['saqr_nogate', hot_env(sel), 'hot']
    cases = [case(k, t, i, s) for k in g4.MESHES for t in g4.TRAFFIC for i in range(9) for s in G5_SEEDS]
    return dict(stage='saqr_h_g5_heldout', seeds=G5_SEEDS, meshes=g4.MESHES, modes=g4.MODES, cases=cases,
                routes=routes, candidates=['saqr_sc', 'saqr_h'], selected_variant=sel, binaries=binaries(),
                binary_sha256={b: sha(ROOT / p) for b, p in binaries().items()},
                source_sha256={s: sha(ROOT / s) for s in SOURCES},
                pilot_selection_sha256=sha(PILOT_DIR / 'selection.json'),
                criteria='scripts/evaluate_saqr_g4.py unchanged (hash in source_sha256)')


def select():
    """Apply the pilot selection rule to the pilot receipts; writes selection.json and SUMMARY.md."""
    proto = json.loads((PILOT_DIR / 'protocol.json').read_text())
    T = 4.303

    def m(c, r):
        x = json.loads((PILOT_DIR / 'cases' / c['name'] / f'weighted_{r}' / 'result.json').read_text())
        cl, be = x['qos']['classes']
        return (cl['ejected_flits'] + be['ejected_flits']) / (x['cycles'] * x['k'] ** 2), x
    data = {}
    for c in proto['cases']:
        for r in proto['routes']:
            data[(c['k'], c['traffic'], c['index'], r, c['seed'])] = m(c, r)
    pts = sorted({(c['k'], c['traffic'], c['index']) for c in proto['cases']})
    col = lambda k, t, i, r: [data[(k, t, i, r, s)][0] for s in PILOT_SEEDS]

    def lb(k, t, i, a, b):
        d = [p - q for p, q in zip(col(k, t, i, a), col(k, t, i, b))]; mu = sum(d) / 3
        sd = math.sqrt(sum((v - mu) ** 2 for v in d) / 2); ref = sum(col(k, t, i, b)) / 3
        return 100 * mu / ref, 100 * (mu - T * sd / math.sqrt(3)) / ref
    # Equivalence: h_off must equal saqr_sc exactly (same metrics, different binary).
    eq = all(data[(k, t, i, 'h_off', s)][1]['qos'] == data[(k, t, i, 'saqr_sc', s)][1]['qos'] and
             data[(k, t, i, 'h_off', s)][1]['aggregate'] == data[(k, t, i, 'saqr_sc', s)][1]['aggregate']
             for (k, t, i) in pts for s in PILOT_SEEDS)
    res = {}
    for v in ['saqr_sc'] + CANDIDATE_VARIANTS:
        c1 = [lb(k, t, i, v, 'xy')[1] for (k, t, i) in pts if t in ('uniform', 'bursty')]
        hot_pts = [(k, t, i) for (k, t, i) in pts if t.startswith('hotspot')]
        fails = 0; thr = 0.0; worst = []
        for (k, t, i) in hot_pts:
            best = max(COMPARATORS, key=lambda r: sum(col(k, t, i, r)))
            l = lb(k, t, i, v, best)
            fails += l[1] <= -3; thr += sum(col(k, t, i, v)) / 3; worst.append((round(l[1], 2), f'k{k} {t} l{i} vs {best}'))
        tr = [lb(k, t, i, v, max(COMPARATORS, key=lambda r: sum(col(k, t, i, r))))[0] for (k, t, i) in pts if t == 'transpose']
        res[v] = dict(uniform_bursty_ok=min(c1) > -3, worst_uniform_bursty_lb=round(min(c1), 2), hotspot_fails=fails,
                      hotspot_points=len(hot_pts), mean_hotspot_thr=thr / len(hot_pts), transpose_vs_best_mean_pct=[round(x, 1) for x in tr],
                      worst_hotspot=sorted(worst)[:4],
                      adaptive_pct={f'k{k} {t}': round(100 * sum(sum(x[1] for x in data[(k, t, i, v, s)][1]['saqr']['src']['marked']) for i in PILOT_INDICES[t] for s in PILOT_SEEDS) /
                                                       max(1, sum(sum(map(sum, data[(k, t, i, v, s)][1]['saqr']['src']['marked'])) for i in PILOT_INDICES[t] for s in PILOT_SEEDS)), 1)
                                    for k in PILOT_MESHES for t in PILOT_INDICES})
    elig = [v for v in CANDIDATE_VARIANTS if res[v]['uniform_bursty_ok']]
    best = None
    if elig:
        best = min(elig, key=lambda v: (res[v]['hotspot_fails'], -res[v]['mean_hotspot_thr']))
        if 'h11' in elig and res['h11']['hotspot_fails'] == res[best]['hotspot_fails'] and \
                res['h11']['mean_hotspot_thr'] >= 0.995 * res[best]['mean_hotspot_thr']:
            best = 'h11'
    out = dict(rule='see scripts/saqr_h_study.py docstring', h_off_equals_saqr_sc=eq, results=res, eligible=elig, selected=best)
    (PILOT_DIR / 'selection.json').write_text(json.dumps(out, indent=1) + '\n')
    return out


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['select']:
        print(json.dumps(select(), indent=1))
