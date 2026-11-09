"""Comparator-binary checks (run on Actions after building .deps/booksim2_saqr_x).

1. Equivalence: shared routes on the new binary reproduce the frozen binaries exactly
   (duato and xy vs the G4 SAQR binary; saqr_h settings vs the SAQR-H binary):
   aggregate and per-class QoS metrics identical.
2. Smoke: DBAR and Footprint on 8x8 cases (uniform, transpose, hotspot_edge, bitcomp,
   multiflow) finish with zero integrity errors; their Duato-framework escape invariant is
   checked by the simulator on every head flit (a violation aborts the run).
Tuning seed 101 only (never a held-out seed). Writes a JSON receipt; exits non-zero on failure.
"""
import json
import sys
import tempfile
from pathlib import Path

from common import ROOT
import saqr_h_study as hs
import traffic_ext
from saqr_hot_common import SAQR_STUDY, SAQR_BINARY, HOT_BINARY, run, sha, trace

X = ROOT / '.deps/booksim2_saqr_x/src/booksim'
OUT = SAQR_STUDY / 'x_smoke'


def thr(r):
    c, b = r['qos']['classes']
    return (c['ejected_flits'] + b['ejected_flits']) / (r['cycles'] * r['k'] ** 2)


def main():
    rows = []; ok = True
    cases = [('uniform', 6), ('uniform', 8), ('transpose', 8), ('hotspot_edge', 5), ('bitcomp', 8), ('multiflow', 8)]
    for t, i in cases:
        c = hs.case(8, t, i, 101); d = OUT / c['name']; d.mkdir(parents=True, exist_ok=True); dem = d / 'demand.txt'
        if t in traffic_ext.PATTERNS: traffic_ext.trace(dem, 8, c['load'], 101, t)
        else: trace(dem, 8, c['load'], 101, t)
        same = lambda a, b: a['qos'] == b['qos'] and a['aggregate'] == b['aggregate']
        if t in ('uniform', 'transpose', 'hotspot_edge'):
            for alg in ('duato', 'xy'):
                a = run(d / f'{alg}_frozen', dem, 8, alg, 101, 'weighted', binary=SAQR_BINARY)
                b = run(d / f'{alg}_x', dem, 8, alg, 101, 'weighted', binary=X)
                rows.append(dict(check=f'equiv {alg}', case=c['name'], ok=same(a, b))); ok &= same(a, b)
            a = run(d / 'h11_hot', dem, 8, 'saqr_nogate', 101, 'weighted', chr_env=hs.hot_env('h11'), binary=HOT_BINARY)
            b = run(d / 'h11_x', dem, 8, 'saqr_nogate', 101, 'weighted', chr_env=hs.hot_env('h11'), binary=X)
            rows.append(dict(check='equiv saqr_h', case=c['name'], ok=same(a, b))); ok &= same(a, b)
        for alg in ('dbar', 'footprint', 'duato'):
            r = run(d / f'{alg}_smoke', dem, 8, alg, 101, 'weighted', binary=X)
            good = r['qos']['integrity_errors'] == 0
            rows.append(dict(check=f'smoke {alg}', case=c['name'], ok=good, throughput=round(thr(r), 5),
                             crit_p99=r['qos']['classes'][0]['latency_p99_cycles'])); ok &= good
    rec = dict(status='pass' if ok else 'fail', x_binary_sha256=sha(X), rows=rows)
    Path(sys.argv[1]).write_text(json.dumps(rec, indent=1) + '\n')
    for r in rows: print(r)
    print('X SMOKE', rec['status'])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
