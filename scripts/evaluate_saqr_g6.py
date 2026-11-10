"""Pre-registered G6 evaluator (written and hashed into results/saqr_study/g6/protocol.json
before any G6 run; margins are constants and are not changed after data is seen).

Identical to scripts/evaluate_saqr_g5.py except for the directory and the comparator set,
which now has nine routes (G5's eight plus classic O1TURN). Candidates: saqr_c, saqr_h.
Criteria, per candidate, weighted mode, every mesh x traffic x load point:
 BT-T  throughput lower bound vs the highest-mean-throughput comparator > -3 %.
 BT-L  critical p99 upper bound vs the lowest-mean-p99 comparator < max(10 %, 5 cycles),
       at points where that comparator's critical pending growth <= 1 % of generated
       critical packets (pooled over seeds); saturated points are judged by BT-T only.
 XY    throughput lower bound vs XY > -3 %.
 S     safety: zero integrity errors, zero failed runs.
Reported, not pass/fail: strict wins (throughput lower bound vs the best comparator > +3 %).
Statistics and margins are imported unchanged from scripts/evaluate_saqr_g4.py
(paired over the 5 seeds, two-sided t 95 % bounds, -3 % throughput, p99 max(10 %, 5 cycles)).
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from evaluate_saqr_g4 import metrics, paired, THR_MARGIN, P99_REL, CRIT_ABS, XY_PENDING
from chr_common import SAQR_STUDY

G6 = SAQR_STUDY / 'g6'


def main(out_dir=None):
    out = Path(out_dir) if out_dir else G6
    proto = json.loads((G6 / 'protocol.json').read_text())
    comps, cands, seeds = proto['comparators'], proto['candidates'], proto['seeds']
    data = {}; missing = defaultdict(int); integrity = 0
    for c in proto['cases']:
        for r in comps + cands:
            f = G6 / 'cases' / c['name'] / f'weighted_{r}' / 'result.json'
            if not f.exists(): missing[(c['k'], c['traffic'])] += 1; continue
            m = metrics(json.loads(f.read_text())); integrity += m['integrity']
            data[(c['k'], c['traffic'], c['index'], r, c['seed'])] = m
    pts = sorted({(c['k'], c['traffic'], c['index']) for c in proto['cases'] if missing[(c['k'], c['traffic'])] == 0})
    col = lambda k, t, i, r, m: [data[(k, t, i, r, s)][m] for s in seeds]
    mean = lambda k, t, i, r, m: sum(col(k, t, i, r, m)) / len(seeds)
    checks = defaultdict(list); rows = []
    for cnd in cands:
        for (k, t, i) in pts:
            where = f'k{k} {t} l{i}'
            bt = max(comps, key=lambda r: mean(k, t, i, r, 'throughput'))
            p = paired(col(k, t, i, cnd, 'throughput'), col(k, t, i, bt, 'throughput'))
            checks[(cnd, 'BT-T', t)].append(dict(where=where, ref=bt, value=p['rel_lo'], ok=p['rel_lo'] > THR_MARGIN, win=p['rel_lo'] > 3))
            bl = min(comps, key=lambda r: mean(k, t, i, r, 'crit_p99'))
            g = sum(col(k, t, i, bl, 'crit_growth')); n = sum(col(k, t, i, bl, 'crit_generated'))
            if n and g <= XY_PENDING * n:
                p = paired(col(k, t, i, cnd, 'crit_p99'), col(k, t, i, bl, 'crit_p99')); lim = max(P99_REL * p['ref_mean'], CRIT_ABS)
                checks[(cnd, 'BT-L', t)].append(dict(where=where, ref=bl, value=p['hi'], limit=lim, ok=p['hi'] < lim))
            p = paired(col(k, t, i, cnd, 'throughput'), col(k, t, i, 'xy', 'throughput'))
            checks[(cnd, 'XY', t)].append(dict(where=where, ref='xy', value=p['rel_lo'], ok=p['rel_lo'] > THR_MARGIN))
            rows.append(dict(candidate=cnd, k=k, traffic=t, index=i, **{f'thr_{r}': mean(k, t, i, r, 'throughput') for r in comps + cands},
                             **{f'p99_{r}': mean(k, t, i, r, 'crit_p99') for r in comps + cands}))
    traffic = proto['traffic']
    lines = ['# G6 fresh held-out: best-or-tied-best verdict', '',
             f"Seeds {seeds}; meshes {proto['meshes']}; {len(traffic)} traffic patterns; comparators {comps}; candidates {cands}.",
             f"Complete (mesh, traffic) groups: {len({(k, t) for k, t, _ in pts})} of {len(proto['meshes'])*len(traffic)}. "
             f"Safety: integrity errors {integrity}.", '',
             'Each cell: passes / checks (strict wins = throughput lower bound > +3 % over the best comparator).', '']
    for cnd in cands:
        lines += [f'## {cnd}', '', '| traffic | BT-T (throughput vs best) | strict wins | BT-L (crit p99 vs best) | never worse than XY |', '|---|---:|---:|---:|---:|']
        tot = defaultdict(lambda: [0, 0])
        for t in traffic:
            cell = []
            for crit in ('BT-T', 'WIN', 'BT-L', 'XY'):
                v = checks.get((cnd, 'BT-T' if crit == 'WIN' else crit, t), [])
                ok = sum(x['win'] for x in v) if crit == 'WIN' else sum(x['ok'] for x in v)
                tot[crit][0] += ok; tot[crit][1] += len(v); cell.append(f'{ok}/{len(v)}')
            lines.append(f'| {t} | ' + ' | '.join(cell) + ' |')
        lines.append('| **all** | ' + ' | '.join(f'**{tot[c][0]}/{tot[c][1]}**' for c in ('BT-T', 'WIN', 'BT-L', 'XY')) + ' |')
        fails = [(crit, x) for (c2, crit, t), v in checks.items() if c2 == cnd for x in v if not x['ok']]
        if fails:
            lines += ['', '| failed check | where | vs | value | limit |', '|---|---|---|---:|---:|']
            lines += [f"| {crit} | {x['where']} | {x['ref']} | {x['value']:.2f} | {x.get('limit', THR_MARGIN):.2f} |" for crit, x in sorted(fails, key=lambda z: z[1]['where'])]
        lines.append('')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'G6_VERDICT.md').write_text('\n'.join(lines) + '\n')
    (out / 'g6_checks.json').write_text(json.dumps({f'{a}|{b}|{c}': v for (a, b, c), v in checks.items()}, indent=1) + '\n')
    if rows:
        with (out / 'g6_summary.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print('\n'.join(lines))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
