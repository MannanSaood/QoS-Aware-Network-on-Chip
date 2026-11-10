"""SAQR-CT binary checks (run on Actions after building .deps/booksim2_saqr_ct).

1. Equivalence: with the gate unset the SAQR-CT binary reproduces the SAQR-C binary exactly on
   c25, and the comparator binary on saqr_h and xy.
2. Smoke: both pilot variants finish with zero integrity errors on 8x8 / 16x16 cases; the share of
   packets marked adaptive is reported (expected: butterfly high, bitcomp/tornado near zero,
   transpose high). Tuning seed 101 only. Writes a JSON receipt; exits non-zero on failure.
"""
import json
import sys
from pathlib import Path

from common import ROOT
import saqr_ct_study as ts
import saqr_c_study as cs
import saqr_h_study as hs
import saqr_g6_study as g6
import saqr_g5_study as g5
from saqr_ct_common import SAQR_STUDY, CT_BINARY, COL_BINARY, run, sha

X = ROOT / '.deps/booksim2_saqr_x/src/booksim'
OUT = SAQR_STUDY / 'ct_smoke'


def main():
    rows = []; ok = True
    same = lambda a, b: a['qos'] == b['qos'] and a['aggregate'] == b['aggregate']
    for k, t, i in [(8, 'butterfly', 7), (8, 'bitcomp', 8), (8, 'transpose', 8), (16, 'tornado', 7), (8, 'shuffle', 7), (8, 'hotspot_edge', 5), (8, 'randperm', 7)]:
        c = g5.case(k, t, i, 101); d = OUT / c['name']; d.mkdir(parents=True, exist_ok=True); dem = d / 'demand.txt'
        if not dem.exists(): g6.make_trace(dem, c)
        if k == 8 and t in ('butterfly', 'transpose', 'hotspot_edge'):
            for name, alg, env, ref in (('c25', 'saqr_nogate', cs.col_env('c25'), COL_BINARY), ('saqr_h', 'saqr_nogate', hs.hot_env('h13'), X), ('xy', 'xy', {}, X)):
                a = run(d / f'{name}_ref', dem, k, alg, 101, 'weighted', chr_env=env, binary=ref)
                b = run(d / f'{name}_ct', dem, k, alg, 101, 'weighted', chr_env=env, binary=CT_BINARY)
                rows.append(dict(check=f'equiv {name}', case=c['name'], ok=same(a, b))); ok &= same(a, b)
        for v in ts.VARIANTS:
            r = run(d / v, dem, k, 'saqr_nogate', 101, 'weighted', chr_env=ts.ct_env(v), binary=CT_BINARY)
            s = json.loads((d / v / 'saqr.json').read_text()); m = s['col']['marked']
            good = r['qos']['integrity_errors'] == 0 and s['ct']['thr'] == ts.VARIANTS[v]
            share = (m[0][1] + m[1][1]) / max(1, sum(m[0]) + sum(m[1]))
            rows.append(dict(check=f'smoke {v}', case=c['name'], ok=good, adaptive_share=round(share, 3), ct=s['ct'])); ok &= good
    rec = dict(status='pass' if ok else 'fail', ct_binary_sha256=sha(CT_BINARY), rows=rows)
    Path(sys.argv[1]).write_text(json.dumps(rec, indent=1) + '\n')
    for r in rows: print(r)
    print('CT SMOKE', rec['status'])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
