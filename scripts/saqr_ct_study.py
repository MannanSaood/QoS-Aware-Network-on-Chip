"""SAQR-CT study (docs/SAQR_SPEC_V2.md §23): design pilot and selection rule, fixed before any pilot run.

Design data: seeds 301-302 (G5 seeds, design data since §21.6) on all 15 G6 patterns, meshes
4-32, load indices 3-8. Butterfly and randperm were never run on these seeds, so this pilot also
runs every comparator and SAQR-C (c25) there; for the 13 other patterns their receipts already
exist (G5, O1TURN stage, SAQR-C pilot) and are reused unchanged.

Groups:
  A  all 15 patterns:            ct16, ct32 (SAQR-CT binary)
  B  butterfly, randperm only:   the nine comparators (comparator binary) and c25 (SAQR-C binary)
Variants (SAQR-C c25 column cue, frozen SAQR-SC settings, SAQR-H h13):
  ct16  SAQR-H bit used where transit evidence r < 16 (half a transit flit per injected packet)
  ct32  SAQR-H bit used where r < 32 (one transit flit per injected packet)
Selection rule (pilot score, means over the two seeds, every pilot point):
  1. most points with throughput >= 0.97 x the best of the nine comparators;
  2. tie: fewest points with throughput < 0.97 x XY;
  3. tie: order c25, ct16, ct32.
If c25 is selected, SAQR-CT brings no improvement and no new held-out is run for it.
"""
import json
import saqr_ct_common  # noqa: F401  (whitelists NOC_SAQR_CT_THR)
from saqr_ct_common import ROOT, CT_BINARY, CT_STUDY, COL_BINARY, sha
import saqr_g5_study as g5
import saqr_g6_study as g6
import saqr_c_study as cs
import run_saqr_g4 as g4

PILOT_DIR = CT_STUDY / 'pilot'
SEEDS = [301, 302]
INDICES = [3, 4, 5, 6, 7, 8]
NINE = cs.NINE
NEW = ['butterfly', 'randperm']
VARIANTS = {'ct16': 16, 'ct32': 32}
SOURCES = ['scripts/saqr_ct_study.py', 'scripts/saqr_ct_common.py', 'scripts/setup_saqr_ct.py',
           'algorithms/saqr_ct/routing.hpp', 'simulators/booksim_saqr_ct/saqr_routes.cpp']
make_trace = g6.make_trace


def ct_env(name):
    return {**cs.col_env('c25'), 'NOC_SAQR_CT_THR': VARIANTS[name]}


def pilot_protocol():
    case = lambda k, t, i, s: g5.case(k, t, i, s)
    all_cases = [case(k, t, i, s) for k in g5.MESHES for t in g6.TRAFFIC for i in INDICES for s in SEEDS]
    new_cases = [c for c in all_cases if c['traffic'] in NEW]
    ra = {n: ['saqr_nogate', ct_env(n), 'ct'] for n in VARIANTS}
    rb = {n: [g4.VARIANTS[n][0], g4.VARIANTS[n][1], 'x'] for n in NINE[:6]}
    rb.update(dbar=['dbar', {}, 'x'], footprint=['footprint', {}, 'x'], o1turn=['o1turn', {}, 'x'], c25=['saqr_nogate', cs.col_env('c25'), 'c'])
    binaries = {'ct': str(CT_BINARY.relative_to(ROOT)), 'c': str(COL_BINARY.relative_to(ROOT)), 'x': str(g5.X_BINARY.relative_to(ROOT))}
    return dict(stage='saqr_ct_pilot', seeds=SEEDS, meshes=g5.MESHES, modes=['weighted'], traffic=g6.TRAFFIC,
                cases=all_cases, groups=[dict(cases=[c['name'] for c in all_cases], routes=ra), dict(cases=[c['name'] for c in new_cases], routes=rb)],
                routes={**ra, **rb}, binaries=binaries, binary_sha256={b: sha(ROOT / p) for b, p in binaries.items()},
                source_sha256={s: sha(ROOT / s) for s in SOURCES}, c_pilot_selection_sha256=sha(cs.PILOT_DIR / 'selection.json'),
                warmup=5000, measurement=20000, selection='scripts/saqr_ct_study.py select() (rule in the module docstring)')


def select():
    from evaluate_saqr_g4 import metrics
    proto = json.loads((PILOT_DIR / 'protocol.json').read_text())
    S = g5.SAQR_STUDY
    def where(r, t):
        if r in VARIANTS or t in NEW: return PILOT_DIR
        if r == 'o1turn': return S / 'g5_o1t'
        if r == 'c25': return cs.PILOT_DIR
        return S / 'g5'
    names = {(c['k'], c['traffic'], c['index'], c['seed']): c['name'] for c in proto['cases']}
    pts = sorted({(c['k'], c['traffic'], c['index']) for c in proto['cases']})
    def mean(p, r):
        k, t, i = p
        return sum(metrics(json.loads((where(r, t) / 'cases' / names[(k, t, i, s)] / f'weighted_{r}' / 'result.json').read_text()))['throughput'] for s in SEEDS) / len(SEEDS)
    ref = {(p, r): mean(p, r) for p in pts for r in NINE}
    score = {}
    for v in ['c25'] + list(VARIANTS):
        good = below = 0; fails = []
        for p in pts:
            m = mean(p, v); best = max(ref[(p, r)] for r in NINE)
            if m >= .97 * best: good += 1
            else: fails.append((f'k{p[0]} {p[1]} l{p[2]}', max(NINE, key=lambda r: ref[(p, r)]), round(100 * (m / best - 1), 1)))
            below += m < .97 * ref[(p, 'xy')]
        score[v] = dict(best_or_tied=good, below_xy=below, points=len(pts), fails=fails)
    order = ['c25'] + list(VARIANTS)
    sel = sorted(order, key=lambda v: (-score[v]['best_or_tied'], score[v]['below_xy'], order.index(v)))[0]
    out = dict(selected=sel, rule='max best_or_tied; then min below_xy; then order c25, ct16, ct32', score=score,
               pilot_protocol_sha256=sha(PILOT_DIR / 'protocol.json'))
    (PILOT_DIR / 'selection.json').write_text(json.dumps(out, indent=1) + '\n')
    return out


if __name__ == '__main__':
    r = select()
    print('selected', r['selected'])
    for v, s in r['score'].items(): print(v, s['best_or_tied'], '/', s['points'], 'below_xy', s['below_xy'])
