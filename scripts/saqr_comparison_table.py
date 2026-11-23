"""Performance comparison table for the deck and report: SAQR-C against the nine comparators.

Data: the frozen G6 receipts (seeds 401-405, 4 meshes x 15 patterns x 9 loads) and the Netrace
receipts (8x8, 3 PARSEC benchmarks x 9 loads, seeds 601-603). Means over seeds per point.
Columns (one definition for every route):
  thr_rel      saturation throughput: geometric mean over the 60 (mesh, pattern) groups of the
               route's mean delivered throughput at the highest load, relative to XY.
  p99_rel      critical-class p99 latency at the high load (index 7 of 9), geometric mean relative to XY.
  cong_top     congested port-time (%) at the highest load, mean over the 60 groups.
  tied_g6      share of the 540 G6 points where the route's mean throughput is >= 0.97 x the best
               of all ten routes.
  tied_nt      the same over the 27 Netrace points.
  wtl          SAQR-C vs this route on G6 (paired over seeds, frozen margins): wins (lower bound
               > +3 %), ties (lower bound > -3 %), clear losses (upper bound < -3 %).
usage: python scripts/saqr_comparison_table.py OUT.json
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_saqr_g4 import metrics, paired, THR_MARGIN  # noqa: E402
from chr_common import SAQR_STUDY  # noqa: E402

ROUTES = ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint', 'o1turn', 'saqr_c']


def load(stage):
    p = json.loads((SAQR_STUDY / stage / 'protocol.json').read_text())
    d = defaultdict(dict)
    for c in p['cases']:
        for r in ROUTES:
            m = metrics(json.loads((SAQR_STUDY / stage / 'cases' / c['name'] / f'weighted_{r}' / 'result.json').read_text()))
            m['congested'] = json.loads((SAQR_STUDY / stage / 'cases' / c['name'] / f'weighted_{r}' / 'result.json').read_text())['aggregate']['congested_port_time_pct']
            d[(c['k'], c['traffic'], c['index'])][(r, c['seed'])] = m
    return p, d


def main():
    out = {}
    gp, g = load('g6'); npr, n = load('nt')
    mean = lambda d, pt, r, key, seeds: sum(d[pt][(r, s)][key] for s in seeds) / len(seeds)
    groups = sorted({(k, t) for k, t, _ in g})
    for r in ROUTES:
        thr = [math.log(mean(g, (k, t, 8), r, 'throughput', gp['seeds']) / mean(g, (k, t, 8), 'xy', 'throughput', gp['seeds'])) for k, t in groups]
        p99 = [math.log(max(1, mean(g, (k, t, 7), r, 'crit_p99', gp['seeds'])) / max(1, mean(g, (k, t, 7), 'xy', 'crit_p99', gp['seeds']))) for k, t in groups]
        cong = [mean(g, (k, t, 8), r, 'congested', gp['seeds']) for k, t in groups]
        tied = lambda d, seeds: sum(mean(d, pt, r, 'throughput', seeds) >= .97 * max(mean(d, pt, q, 'throughput', seeds) for q in ROUTES) for pt in d)
        row = dict(thr_rel=math.exp(sum(thr) / len(thr)), p99_rel=math.exp(sum(p99) / len(p99)), cong_top=sum(cong) / len(cong),
                   tied_g6=tied(g, gp['seeds']), n_g6=len(g), tied_nt=tied(n, npr['seeds']), n_nt=len(n))
        if r != 'saqr_c':
            w = t_ = l = 0
            for pt in g:
                pr = paired([g[pt][('saqr_c', s)]['throughput'] for s in gp['seeds']], [g[pt][(r, s)]['throughput'] for s in gp['seeds']])
                if pr['rel_lo'] > 3: w += 1
                elif pr['rel_hi'] < -3: l += 1
                elif pr['rel_lo'] > THR_MARGIN: t_ += 1
            row['wtl'] = [w, t_, l]
        out[r] = row
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + '\n')
    for r, v in out.items():
        print(f"{r:10s} thr x{v['thr_rel']:.3f} p99 x{v['p99_rel']:.2f} cong {v['cong_top']:.2f}% tiedG6 {100*v['tied_g6']/v['n_g6']:.0f}% tiedNT {100*v['tied_nt']/v['n_nt']:.0f}% wtl {v.get('wtl')}")


if __name__ == '__main__':
    main()
