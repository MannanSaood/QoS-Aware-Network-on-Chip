"""Netrace application traces (docs/SAQR_SPEC_V2.md §24). Defined before any Netrace run.

Traces: PARSEC 2.1 simsmall, 64 cores (blackscholes, fluidanimate, x264) from Netrace 1.0,
converted on GitHub Actions by ci/netrace/convert.c (region of interest, one window per benchmark
starting 10 % into it, time-compressed into the study window; nine load points keep 2-100 % of
the window's packets by packet-id hash; timestamp replay, dependencies not enforced, control packets critical / data packets best effort, 5-flit packets). The converted
traces are identified by their sha256 (from the conversion run's manifest) and are never
committed. Mesh 8x8 (the traces' 64 nodes). Simulator seeds 601-603. Weighted QoS mode.
Routes: the nine comparators, saqr_h (h13), saqr_c (c25) and saqr_ct (variant chosen by the
SAQR-CT pilot). Scoring: scripts/evaluate_saqr_nt.py (G6 criteria, three seeds).
"""
import json
import os
import shutil
from pathlib import Path
import saqr_ct_common  # noqa: F401
from saqr_ct_common import ROOT, SAQR_STUDY, CT_BINARY, COL_BINARY, sha
import saqr_g5_study as g5
import saqr_c_study as cs
import saqr_ct_study as ts
import saqr_h_study as hs

NT_DIR = SAQR_STUDY / 'nt'
MANIFEST = NT_DIR / 'trace_manifest.json'      # copied from the conversion run's artifact
SEEDS = [601, 602, 603]
BENCHMARKS = ['blackscholes', 'fluidanimate', 'x264']
COMPARATORS = ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint', 'o1turn']
SOURCES = ['scripts/saqr_nt_study.py', 'scripts/evaluate_saqr_nt.py', 'ci/netrace/convert.c', 'ci/netrace/convert.sh',
           'scripts/saqr_ct_study.py', 'scripts/saqr_c_study.py', 'scripts/evaluate_saqr_g4.py']


def cases():
    m = json.loads(MANIFEST.read_text())
    out = []
    for b in BENCHMARKS:
        fs = sorted((v for v in m.values() if v['benchmark'] == b), key=lambda v: v['keep_permille'])
        for i, v in enumerate(fs):
            for s in SEEDS:
                out.append(dict(k=8, traffic=f'nt_{b}', index=i, load=v['offered_flits_per_node_cycle'], seed=s,
                                factor=v['factor'], keep_permille=v['keep_permille'], trace=f"{b}_q{v['keep_permille']}",
                                trace_sha256=v['sha256'], name=f"k8_nt_{b}_q{v['keep_permille']}_s{s}"))
    return out


def make_trace(path, c):
    """Copy the converted trace (downloaded from the conversion run into $NT_TRACE_DIR) and check its hash."""
    src = Path(os.environ['NT_TRACE_DIR']) / 'traces' / f"{c['trace']}.txt"
    assert sha(src) == c['trace_sha256'], f"converted trace {src} does not match the frozen hash"
    shutil.copyfile(src, path)
    return sum(1 for _ in open(path))


def protocol():
    sel = json.loads((ts.PILOT_DIR / 'selection.json').read_text())['selected']
    import run_saqr_g4 as g4
    routes = {n: [g4.VARIANTS[n][0], g4.VARIANTS[n][1], 'x'] for n in COMPARATORS[:6]}
    routes.update(dbar=['dbar', {}, 'x'], footprint=['footprint', {}, 'x'], o1turn=['o1turn', {}, 'x'])
    routes['saqr_h'] = ['saqr_nogate', hs.hot_env('h13'), 'x']
    routes['saqr_c'] = ['saqr_nogate', cs.col_env('c25'), 'c']
    cands = ['saqr_h', 'saqr_c']
    if sel in ts.VARIANTS:
        routes['saqr_ct'] = ['saqr_nogate', ts.ct_env(sel), 'ct']; cands.append('saqr_ct')
    binaries = {'x': str(g5.X_BINARY.relative_to(ROOT)), 'c': str(COL_BINARY.relative_to(ROOT)), 'ct': str(CT_BINARY.relative_to(ROOT))}
    cs_ = cases()
    return dict(stage='saqr_netrace', seeds=SEEDS, meshes=[8], modes=['weighted'], traffic=[f'nt_{b}' for b in BENCHMARKS],
                cases=cs_, routes=routes, comparators=COMPARATORS, candidates=cands, ct_selected=sel, binaries=binaries,
                binary_sha256={b: sha(ROOT / p) for b, p in binaries.items()}, source_sha256={s: sha(ROOT / s) for s in SOURCES},
                trace_manifest_sha256=sha(MANIFEST), ct_pilot_selection_sha256=sha(ts.PILOT_DIR / 'selection.json'),
                warmup=5000, measurement=20000, criteria='scripts/evaluate_saqr_nt.py (hash in source_sha256)')
