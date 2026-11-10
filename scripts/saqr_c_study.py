"""SAQR-C study (docs/SAQR_SPEC_V2.md §22): design pilot and selection rule, fixed before any pilot run.

Design data: the G5 seeds 301 and 302 (spent as held-out by §21.6, now design data) on
every G5 traffic pattern and mesh, load indices 3-8 (where routes separate). The pilot
runs only the SAQR-C variants; every comparator's receipt for these exact cases (same
trace, same seed) already exists from G5 and the O1TURN stage and is reused unchanged.

Variants (all use the frozen SAQR-SC settings and the selected SAQR-H tracker h13):
  c50   converging bit at share >= 50 % (off 35 %), column cue only
  c25   converging bit at share >= 25 % (off 17.5 %), column cue only
  c50h  c50, plus hotspot-like sources (SAQR-H bit and not SAQR-SC bit)
  c25h  c25, plus hotspot-like sources
Selection rule (pilot score, means over the two seeds, every pilot point):
  1. most points with throughput >= 0.97 x the best of the nine comparators
     (xy, oefixed, dyad, topsis, duato, westfirst, dbar, footprint, o1turn);
  2. tie: fewest points with throughput < 0.97 x XY;
  3. tie: the earlier variant in the order above (simplest first).
The selected variant is then frozen for a fresh held-out (G6, new seeds) defined separately.
"""
import json
import saqr_col_common  # noqa: F401  (whitelists the NOC_SAQR_COL_* variables)
from saqr_col_common import ROOT, COL_BINARY, COL_STUDY, sha
import saqr_g5_study as g5
import saqr_h_study as hs

PILOT_DIR = COL_STUDY / 'pilot'
SEEDS = [301, 302]
INDICES = [3, 4, 5, 6, 7, 8]
NINE = ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint', 'o1turn']
VARIANTS = {'c50': dict(on=2048, off=1434, floor=512, init=1024, shift=5, mode=0),
            'c25': dict(on=1024, off=717, floor=256, init=512, shift=5, mode=0),
            'c50h': dict(on=2048, off=1434, floor=512, init=1024, shift=5, mode=1),
            'c25h': dict(on=1024, off=717, floor=256, init=512, shift=5, mode=1)}
HOT_VARIANT = 'h13'
SOURCES = ['scripts/saqr_c_study.py', 'scripts/saqr_col_common.py', 'scripts/setup_saqr_c.py',
           'algorithms/saqr_col/routing.hpp', 'simulators/booksim_saqr_c/saqr_routes.cpp']
make_trace = g5.make_trace


def col_env(name):
    v = VARIANTS[name]
    return {**hs.hot_env(HOT_VARIANT), 'NOC_SAQR_COL_ON': v['on'], 'NOC_SAQR_COL_OFF': v['off'], 'NOC_SAQR_COL_FLOOR': v['floor'],
            'NOC_SAQR_COL_INIT': v['init'], 'NOC_SAQR_COL_SHIFT': v['shift'], 'NOC_SAQR_COL_MODE': v['mode']}


def pilot_protocol():
    cases = [g5.case(k, t, i, s) for k in g5.MESHES for t in g5.TRAFFIC for i in INDICES for s in SEEDS]
    return dict(stage='saqr_c_pilot', seeds=SEEDS, meshes=g5.MESHES, modes=['weighted'], traffic=g5.TRAFFIC, cases=cases,
                routes={n: ['saqr_nogate', col_env(n), 'c'] for n in VARIANTS}, binaries={'c': str(COL_BINARY.relative_to(ROOT))},
                binary_sha256={'c': sha(COL_BINARY)}, source_sha256={s: sha(ROOT / s) for s in SOURCES},
                g5_protocol_sha256=sha(g5.G5_DIR / 'protocol.json'), warmup=5000, measurement=20000,
                selection='scripts/saqr_c_study.py select() (rule in the module docstring)')


def select():
    """Apply the fixed rule to the pilot receipts and the reused G5 / O1TURN receipts."""
    from evaluate_saqr_g4 import metrics
    proto = json.loads((PILOT_DIR / 'protocol.json').read_text())
    where = lambda r: g5.SAQR_STUDY / ('g5_o1t' if r == 'o1turn' else 'g5')
    pts = sorted({(c['k'], c['traffic'], c['index']) for c in proto['cases']})
    byname = {(c['k'], c['traffic'], c['index'], c['seed']): c['name'] for c in proto['cases']}
    thr = lambda base, name, r: metrics(json.loads((base / 'cases' / name / f'weighted_{r}' / 'result.json').read_text()))['throughput']
    mean = lambda k, t, i, r, base: sum(thr(base, byname[(k, t, i, s)], r) for s in SEEDS) / len(SEEDS)
    ref = {(p, r): mean(*p, r, where(r)) for p in pts for r in NINE + ['saqr_h']}
    score = {}
    for v in list(VARIANTS) + ['saqr_h']:
        good = below_xy = 0; fails = []
        for p in pts:
            m = ref[(p, v)] if v == 'saqr_h' else mean(*p, v, PILOT_DIR)
            best = max(ref[(p, r)] for r in NINE)
            if m >= .97 * best: good += 1
            else: fails.append((f'k{p[0]} {p[1]} l{p[2]}', max(NINE, key=lambda r: ref[(p, r)]), round(100 * (m / best - 1), 1)))
            below_xy += m < .97 * ref[(p, 'xy')]
        score[v] = dict(best_or_tied=good, below_xy=below_xy, points=len(pts), fails=fails)
    order = list(VARIANTS)
    sel = sorted(order, key=lambda v: (-score[v]['best_or_tied'], score[v]['below_xy'], order.index(v)))[0]
    out = dict(selected=sel, rule='max best_or_tied; then min below_xy; then variant order', score=score,
               pilot_protocol_sha256=sha(PILOT_DIR / 'protocol.json'))
    (PILOT_DIR / 'selection.json').write_text(json.dumps(out, indent=1) + '\n')
    return out


if __name__ == '__main__':
    r = select()
    print('selected', r['selected'])
    for v, s in r['score'].items(): print(v, s['best_or_tied'], '/', s['points'], 'below_xy', s['below_xy'])
