"""SAQR-C binary checks (run on Actions after building .deps/booksim2_saqr_c).

1. Equivalence: with the column cue unset, the SAQR-C binary reproduces the comparator binary
   exactly on saqr_h (h13), xy and dbar (aggregate and per-class QoS metrics identical).
2. Smoke: every pilot variant on 8x8 and 16x16 cases finishes with zero integrity errors (the
   CTY invariant is checked by the simulator on every head flit); the share of packets marked
   adaptive is reported per pattern (expected: high on transpose, low on bitcomp/tornado).
Tuning seed 101 only (never a held-out seed). Writes a JSON receipt; exits non-zero on failure.
"""
import json
import sys
from pathlib import Path

from common import ROOT
import saqr_c_study as cs
import saqr_h_study as hs
import saqr_g5_study as g5
from saqr_col_common import SAQR_STUDY, COL_BINARY, run, sha

X = ROOT / '.deps/booksim2_saqr_x/src/booksim'
OUT = SAQR_STUDY / 'c_smoke'


def main():
    rows = []; ok = True
    same = lambda a, b: a['qos'] == b['qos'] and a['aggregate'] == b['aggregate']
    for k, t, i in [(8, 'uniform', 7), (8, 'transpose', 8), (8, 'hotspot_edge', 5), (8, 'bitcomp', 8), (16, 'tornado', 7), (16, 'transpose', 7), (8, 'mixed', 7)]:
        c = g5.case(k, t, i, 101); d = OUT / c['name']; d.mkdir(parents=True, exist_ok=True); dem = d / 'demand.txt'
        if not dem.exists(): g5.make_trace(dem, c)
        if k == 8 and t in ('uniform', 'transpose', 'hotspot_edge'):
            for alg, env in (('saqr_nogate', hs.hot_env(cs.HOT_VARIANT)), ('xy', {}), ('dbar', {})):
                a = run(d / f'{alg}_x', dem, k, alg, 101, 'weighted', chr_env=env, binary=X)
                b = run(d / f'{alg}_c', dem, k, alg, 101, 'weighted', chr_env=env, binary=COL_BINARY)
                rows.append(dict(check=f'equiv {alg}', case=c['name'], ok=same(a, b))); ok &= same(a, b)
        for v in cs.VARIANTS:
            r = run(d / v, dem, k, 'saqr_nogate', 101, 'weighted', chr_env=cs.col_env(v), binary=COL_BINARY)
            s = json.loads((d / v / 'saqr.json').read_text())['col']; m = s['marked']
            good = r['qos']['integrity_errors'] == 0 and s['on'] == cs.VARIANTS[v]['on']
            share = (m[0][1] + m[1][1]) / max(1, sum(m[0]) + sum(m[1]))
            rows.append(dict(check=f'smoke {v}', case=c['name'], ok=good, adaptive_share=round(share, 3), observed=s['observed'])); ok &= good
    rec = dict(status='pass' if ok else 'fail', c_binary_sha256=sha(COL_BINARY), rows=rows)
    Path(sys.argv[1]).write_text(json.dumps(rec, indent=1) + '\n')
    for r in rows: print(r)
    print('C SMOKE', rec['status'])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
