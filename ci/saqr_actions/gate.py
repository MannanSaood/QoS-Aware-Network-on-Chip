"""Reproduction gate on the Actions runner (must pass before any lane result is trusted).

1. Both frozen protocols recompute identically from the bundled files (hash check).
2. Held-out traces regenerate byte-identically (sha vs the local receipts), including k = 16.
3. A sample of held-out runs completed locally reproduces bit for bit: aggregate, per-class
   QoS, CHR and SAQR metric blocks, config and binary hashes must all be equal.
4. If the bundle has the SAQR-H binary: every SAQR-SC reference run reproduces on it with the
   tracker off (all metrics equal; only the binary hash and the added 'hot' block differ).
Writes gate.json; exits non-zero on any difference.
"""
import concurrent.futures
import json
import platform
import sys
import tempfile
from pathlib import Path

from common import ROOT, verify_frozen
from chr_common import SAQR_STUDY, run, sha, trace

B = ROOT / 'ci_bundle' / 'gate'
HOT_REL = '.deps/booksim2_saqr_hot/src/booksim'
KEYS = ('aggregate', 'qos', 'chr', 'saqr', 'binary_sha256', 'config_sha256', 'trace_sha256', 'chr_env')


def main():
    out = Path(sys.argv[1])
    verify_frozen()
    import numpy
    m = json.loads((B / 'manifest.json').read_text())
    rows = []
    tmp = Path(tempfile.mkdtemp())
    for t in m['trace_checks']:
        c = t['case']; f = tmp / f"{c['name']}.txt"
        trace(f, c['k'], c['load'], c['seed'], c['traffic'])
        rows.append(dict(check='trace', case=c['name'], ok=sha(f) == t['trace_sha256']))
        f.unlink()

    def one(item):
        c, j = item['case'], item['job']; ref = json.loads((ROOT / 'ci_bundle' / item['ref']).read_text())
        d = SAQR_STUDY / 'ci_gate' / c['name']; d.mkdir(parents=True, exist_ok=True)
        demand = d / 'demand.txt'
        if not demand.exists():
            trace(d / 'demand.tmp', c['k'], c['load'], c['seed'], c['traffic']); (d / 'demand.tmp').replace(demand)
        hot = item.get('hot_equiv', False)
        binary = ROOT / HOT_REL if hot else ROOT / j['binary']
        r = run(d / f"{'hotbin_' if hot else ''}{j['stage']}_{j['mode']}_{j['name']}", demand, c['k'], j['alg'], c['seed'], j['mode'],
                chr_env=j['env'], binary=binary)
        if hot:   # SAQR-H binary, tracker off: everything but the binary hash and the extra 'hot' block must equal SAQR-SC
            strip = lambda x: {**x, 'saqr': {kk: vv for kk, vv in (x.get('saqr') or {}).items() if kk != 'hot'}}
            r, ref = strip(r), strip(ref)
            diff = [k for k in KEYS if k != 'binary_sha256' and r.get(k) != ref.get(k)]
        else:
            diff = [k for k in KEYS if r.get(k) != ref.get(k)]
        return dict(check='hot_equiv' if hot else 'run', case=c['name'], stage=j['stage'], mode=j['mode'], route=j['name'], ok=not diff,
                    differs=diff, wall_seconds=r['wall_seconds'])

    # Group by case so each trace is generated once.
    items = sorted(m['runs'], key=lambda x: x['case']['name'])
    if (ROOT / HOT_REL).exists():   # SAQR-H equivalence: every SAQR-SC reference rerun on the SAQR-H binary, tracker off
        items += [dict(it, hot_equiv=True) for it in items if it['job']['stage'] == 'src']
    by_case = {}
    for it in items:
        by_case.setdefault(it['case']['name'], []).append(it)
    for name, its in by_case.items():           # serial trace generation
        c = its[0]['case']; d = SAQR_STUDY / 'ci_gate' / name; d.mkdir(parents=True, exist_ok=True)
        if not (d / 'demand.txt').exists():
            trace(d / 'demand.tmp', c['k'], c['load'], c['seed'], c['traffic']); (d / 'demand.tmp').replace(d / 'demand.txt')
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        for r in pool.map(one, items):
            rows.append(r); print(r, flush=True)
    status = 'pass' if rows and all(r['ok'] for r in rows) else 'fail'
    rec = dict(status=status, checks=len(rows), passed=sum(r['ok'] for r in rows), rows=rows,
               python=platform.python_version(), numpy=numpy.__version__, bundle_sha256=sha(ROOT / 'ci/saqr_actions/bundle.tar.gz'))
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'GATE {status}: {rec["passed"]}/{rec["checks"]}')
    sys.exit(0 if status == 'pass' else 1)


if __name__ == '__main__':
    main()
