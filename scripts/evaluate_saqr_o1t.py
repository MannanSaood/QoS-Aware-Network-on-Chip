"""Pre-registered evaluator for the O1TURN extension of G5 (scripts/saqr_o1t_study.py),
written and hashed into results/saqr_study/g5_o1t/protocol.json before any of its runs.
Metrics, statistics and margins are imported unchanged from scripts/evaluate_saqr_g4.py
(paired over seeds 301-305, two-sided t 95 % bounds, -3 % throughput, p99 max(10 %, 5 cycles)).

Candidates: saqr_sc and saqr_h (their G5 receipts). New routes: o1turn, saqr_all (this stage).
At every mesh x traffic x load point, weighted mode:
 O-T   candidate throughput lower bound vs o1turn > -3 %.
 O-L   candidate critical p99 upper bound vs o1turn < max(10 %, 5 cycles), at points where
       o1turn's critical pending growth <= 1 % of generated critical packets.
 A-T   candidate throughput lower bound vs saqr_all > -3 % (the classifier never costs throughput).
 B9-T  candidate throughput lower bound vs the best of the nine comparators
       (the eight G5 comparators plus o1turn) > -3 %  (the extended best-or-tied claim).
 S     zero integrity errors, zero failed runs (both stages).
Reported, not pass/fail: strict wins (lower bound > +3 %) for O-T, A-T and B9-T, and the
mean throughput / p99 of every route per point (o1t_summary.csv).
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from evaluate_saqr_g4 import metrics, paired, THR_MARGIN, P99_REL, CRIT_ABS, XY_PENDING
from chr_common import SAQR_STUDY

G5 = SAQR_STUDY / 'g5'
O1T = SAQR_STUDY / 'g5_o1t'


def main(out_dir=None):
    out = Path(out_dir) if out_dir else O1T
    gp = json.loads((G5 / 'protocol.json').read_text()); op = json.loads((O1T / 'protocol.json').read_text())
    comps, cands, seeds, new = gp['comparators'], gp['candidates'], gp['seeds'], list(op['routes'])
    data = {}; missing = defaultdict(int); integrity = 0
    for c in gp['cases']:
        for r in comps + cands + new:
            f = (O1T if r in new else G5) / 'cases' / c['name'] / f'weighted_{r}' / 'result.json'
            if not f.exists(): missing[(c['k'], c['traffic'])] += 1; continue
            m = metrics(json.loads(f.read_text())); integrity += m['integrity']
            data[(c['k'], c['traffic'], c['index'], r, c['seed'])] = m
    pts = sorted({(c['k'], c['traffic'], c['index']) for c in gp['cases'] if missing[(c['k'], c['traffic'])] == 0})
    col = lambda k, t, i, r, m: [data[(k, t, i, r, s)][m] for s in seeds]
    mean = lambda k, t, i, r, m: sum(col(k, t, i, r, m)) / len(seeds)
    nine = comps + ['o1turn']
    checks = defaultdict(list); rows = []
    for cnd in cands:
        for (k, t, i) in pts:
            where = f'k{k} {t} l{i}'
            for crit, ref in (('O-T', 'o1turn'), ('A-T', 'saqr_all'), ('B9-T', max(nine, key=lambda r: mean(k, t, i, r, 'throughput')))):
                p = paired(col(k, t, i, cnd, 'throughput'), col(k, t, i, ref, 'throughput'))
                checks[(cnd, crit, t)].append(dict(where=where, ref=ref, value=p['rel_lo'], ok=p['rel_lo'] > THR_MARGIN, win=p['rel_lo'] > 3))
            g = sum(col(k, t, i, 'o1turn', 'crit_growth')); n = sum(col(k, t, i, 'o1turn', 'crit_generated'))
            if n and g <= XY_PENDING * n:
                p = paired(col(k, t, i, cnd, 'crit_p99'), col(k, t, i, 'o1turn', 'crit_p99')); lim = max(P99_REL * p['ref_mean'], CRIT_ABS)
                checks[(cnd, 'O-L', t)].append(dict(where=where, ref='o1turn', value=p['hi'], limit=lim, ok=p['hi'] < lim, win=False))
        for (k, t, i) in pts:
            rows.append(dict(candidate=cnd, k=k, traffic=t, index=i, **{f'thr_{r}': mean(k, t, i, r, 'throughput') for r in nine + cands + ['saqr_all']},
                             **{f'p99_{r}': mean(k, t, i, r, 'crit_p99') for r in nine + cands + ['saqr_all']}))
    traffic = gp['traffic']; crits = ('O-T', 'O-L', 'A-T', 'B9-T')
    lines = ['# G5 + O1TURN: is the SAQR gain just O1TURN?', '',
             f"Seeds {seeds}; meshes {gp['meshes']}; {len(traffic)} traffic patterns; candidates {cands}; new routes {new}.",
             f"Complete (mesh, traffic) groups: {len({(k, t) for k, t, _ in pts})} of {len(gp['meshes'])*len(traffic)}. Safety: integrity errors {integrity}.", '',
             'Each cell: passes / checks; strict wins (lower bound > +3 %) in brackets.', '']
    for cnd in cands:
        lines += [f'## {cnd}', '', '| traffic | O-T vs o1turn | O-L p99 vs o1turn | A-T vs saqr_all | B9-T vs best of 9 |', '|---|---:|---:|---:|---:|']
        tot = defaultdict(lambda: [0, 0, 0])
        for t in traffic:
            cell = []
            for crit in crits:
                v = checks.get((cnd, crit, t), []); ok = sum(x['ok'] for x in v); w = sum(x['win'] for x in v)
                tot[crit][0] += ok; tot[crit][1] += len(v); tot[crit][2] += w
                cell.append(f'{ok}/{len(v)}' + (f' ({w})' if crit != 'O-L' else ''))
            lines.append(f'| {t} | ' + ' | '.join(cell) + ' |')
        lines.append('| **all** | ' + ' | '.join(f'**{tot[c][0]}/{tot[c][1]}**' + (f' ({tot[c][2]})' if c != 'O-L' else '') for c in crits) + ' |')
        fails = [(crit, x) for (c2, crit, t), v in checks.items() if c2 == cnd for x in v if not x['ok']]
        if fails:
            lines += ['', '| failed check | where | vs | value | limit |', '|---|---|---|---:|---:|']
            lines += [f"| {crit} | {x['where']} | {x['ref']} | {x['value']:.2f} | {x.get('limit', THR_MARGIN):.2f} |" for crit, x in sorted(fails, key=lambda z: z[1]['where'])]
        lines.append('')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'O1T_VERDICT.md').write_text('\n'.join(lines) + '\n')
    (out / 'o1t_checks.json').write_text(json.dumps({f'{a}|{b}|{c}': v for (a, b, c), v in checks.items()}, indent=1) + '\n')
    if rows:
        with (out / 'o1t_summary.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print('\n'.join(lines))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
