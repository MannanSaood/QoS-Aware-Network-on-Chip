"""Merge a wave's lane outputs into the results-branch checkout and write the 6-hourly check report.

usage: status.py RESULTS_CHECKOUT LANE_DIR [GATE_JSON]

- unpacks each lane's result.json files (never overwrites a committed receipt),
- records every trace sha (traces.json) and stops on any conflicting sha,
- appends ci_status/waves.jsonl and rewrites ci_status/STATUS.md,
- writes ci_status/ALERT if anything needs attention (the workflow fails on it after pushing).
"""
import json
import os
import sys
import tarfile
import time
from pathlib import Path

from common import jobs, verify_frozen, ROOT


def main():
    res, lanes = Path(sys.argv[1]), Path(sys.argv[2])
    gate = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 and Path(sys.argv[3]).exists() else None
    st = res / 'ci_status'; st.mkdir(parents=True, exist_ok=True)
    gp, sp = verify_frozen()
    done_local = json.loads((ROOT / 'ci_bundle' / 'done.json').read_text())
    traces = json.loads((st / 'traces.json').read_text()) if (st / 'traces.json').exists() else {}
    alerts = []; wave = dict(time=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), run_id=os.environ.get('GITHUB_RUN_ID'),
                             completed=0, failures=[], interrupted=0, not_started=0, trace_mismatch=[], lanes=0, lane_hours=[])
    if gate is not None:
        wave['gate'] = f"{gate['status']} {gate['passed']}/{gate['checks']}"
        if gate['status'] != 'pass':
            alerts.append(f"reproduction gate FAILED ({wave['gate']}); lanes were not run")
    for rj in sorted(lanes.glob('**/lane*.json')):
        rep = json.loads(rj.read_text()); wave['lanes'] += 1; wave['lane_hours'].append(round(rep['hours'], 2))
        tgz = rj.with_suffix('.tar.gz')
        if tgz.exists():
            with tarfile.open(tgz) as tar:
                for m in tar.getmembers():
                    if not m.isfile() or not m.name.endswith('/result.json') or m.name.startswith('/') or '..' in m.name:
                        continue
                    dst = res / m.name
                    if dst.exists():
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(tar.extractfile(m).read())
                    wave['completed'] += 1
        for case, s in rep['traces'].items():
            if traces.setdefault(case, s) != s:
                alerts.append(f'trace sha conflict for {case}')
        wave['failures'] += rep['failures']; wave['interrupted'] += len(rep['interrupted'])
        wave['not_started'] += rep['not_started']; wave['trace_mismatch'] += rep['trace_mismatch']
    if wave['failures']:
        alerts.append(f"{len(wave['failures'])} run failures this wave (see waves.jsonl)")
    if wave['trace_mismatch']:
        alerts.append(f"trace mismatch vs earlier receipts: {wave['trace_mismatch'][:5]}")
    (st / 'traces.json').write_text(json.dumps(traces, indent=0, sort_keys=True) + '\n')
    with (st / 'waves.jsonl').open('a') as f:
        f.write(json.dumps(wave) + '\n')

    # Progress table: frozen matrices, meshes 4..32, both stages.
    waves = [json.loads(l) for l in (st / 'waves.jsonl').read_text().splitlines() if l.strip()]
    rows = []; remaining = 0
    for k in (4, 8, 16, 32):
        for stage in ('g4', 'src'):
            tot = loc = act = 0
            for c, js in jobs(gp, sp, meshes=[k]):
                for j in js:
                    if j['stage'] != stage:
                        continue
                    tot += 1
                    if j['dir'] in done_local:
                        loc += 1
                    elif (res / j['dir'] / 'result.json').exists():
                        act += 1
            remaining += tot - loc - act
            rows.append(f"| {k}x{k} | {'previous candidates + comparators' if stage == 'g4' else 'SAQR-SC'} | {tot} | {loc} | {act} | {tot-loc-act} | {100*(loc+act)/tot:.1f}% |")
    recent = [w['completed'] for w in waves[-3:] if w.get('lanes')]
    rate = sum(recent) / len(recent) if recent else 0
    eta = f"about {remaining/rate:.1f} more waves (~{6*remaining/rate:.0f} h at one wave per 6 h)" if rate else 'unknown until a wave completes'
    lines = ['# SAQR held-out on GitHub Actions: status', '',
             f"Last check: {wave['time']} (run {wave['run_id']}). Frozen binaries and protocols re-verified by hash in every job.", '',
             f"**Alerts:** {'; '.join(alerts) if alerts else 'none'}", '',
             '| mesh | stage | runs | done locally | done on Actions | remaining | complete |', '|---|---|---:|---:|---:|---:|---:|', *rows, '',
             f'Remaining runs: {remaining}. Throughput (last waves): {rate:.0f} runs/wave. ETA: {eta}.', '',
             '| wave (UTC) | gate | lanes | completed | failed | interrupted (rerun) | not started |', '|---|---|---:|---:|---:|---:|---:|']
    lines += [f"| {w['time']} | {w.get('gate', '-')} | {w['lanes']} | {w['completed']} | {len(w['failures'])} | {w['interrupted']} | {w['not_started']} |" for w in waves[-12:]]
    (st / 'STATUS.md').write_text('\n'.join(lines) + '\n')
    if remaining == 0:
        (st / 'COMPLETE').write_text(wave['time'] + '\n')
    if alerts:
        (st / 'ALERT').write_text('\n'.join(alerts) + '\n')
    elif (st / 'ALERT').exists():
        (st / 'ALERT').unlink()
    print('\n'.join(lines[:8 + len(rows)]))


if __name__ == '__main__':
    main()
