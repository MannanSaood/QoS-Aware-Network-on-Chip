"""Build ci/saqr_actions/bundle.tar.gz locally (run inside the WSL checkout that holds the frozen builds).

The bundle holds, byte-exact:
- the runner scripts, algorithm headers and simulator sources hashed by both frozen protocols,
- both frozen booksim binaries (G4 f34be4ee..., SAQR-SC 4bf9ab50...),
- the receipts the protocols hash (R0 gates, pilot selection, both protocol files),
- done.json: every run already completed locally (path -> trace sha), so Actions skips it,
- gate/: reference receipts for the reproduction gate.
"""
import io
import json
import random
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
import common  # noqa: E402
from common import ROOT, g4, sg4, jobs, verify_frozen  # noqa: E402

FILES = [
    'scripts/qos_common.py', 'scripts/chr_common.py', 'scripts/saqr_src_common.py',
    'scripts/run_saqr_g4.py', 'scripts/run_saqr_src_g4.py', 'scripts/run_saqr_src_pilot.py',
    'scripts/evaluate_saqr_g4.py', 'scripts/setup_saqr.py', 'scripts/setup_saqr_src.py',
    'algorithms/saqr/routing.hpp', 'algorithms/saqr_src/routing.hpp',
    'simulators/booksim_saqr/saqr_routes.cpp', 'simulators/booksim_saqr_src/saqr_routes.cpp',
    '.deps/booksim2_saqr/src/booksim', '.deps/booksim2_saqr_src/src/booksim',
    'results/saqr_study/r0/r0_receipt.json', 'results/saqr_study/g4/protocol.json',
    'results/saqr_study/src/r0/r0_receipt.json', 'results/saqr_study/src/pilot/selection.json',
    'results/saqr_study/src/g4/protocol_src.json',
    # SAQR-H study (§20)
    'scripts/saqr_hot_common.py', 'scripts/saqr_h_study.py', 'scripts/setup_saqr_hot.py',
    'algorithms/saqr_hot/routing.hpp', 'simulators/booksim_saqr_hot/saqr_routes.cpp', 'tests/saqr_hot_test.cpp',
    '.deps/booksim2_saqr_hot/src/booksim',
    # G5 (§21): comparator build, unseen patterns, study definition and evaluator
    'scripts/traffic_ext.py', 'scripts/saqr_g5_study.py', 'scripts/evaluate_saqr_g5.py', 'scripts/setup_saqr_x.py',
    'algorithms/dbar/routing.hpp', 'algorithms/footprint/routing.hpp', 'simulators/booksim_saqr_x/saqr_routes.cpp',
    '.deps/booksim2_saqr_x/src/booksim',
    # O1TURN extension of G5 (§21.7)
    'scripts/saqr_o1t_study.py', 'scripts/evaluate_saqr_o1t.py',
    # SAQR-C (§22)
    'scripts/saqr_col_common.py', 'scripts/saqr_c_study.py', 'scripts/setup_saqr_c.py',
    'algorithms/saqr_col/routing.hpp', 'simulators/booksim_saqr_c/saqr_routes.cpp', '.deps/booksim2_saqr_c/src/booksim',
]
# Stage protocol files, included once they exist (pilot protocol, pilot selection, G5 protocol).
OPTIONAL = ['results/saqr_study/hot/pilot/protocol.json', 'results/saqr_study/hot/pilot/selection.json',
            'results/saqr_study/hot/g5/protocol.json', 'results/saqr_study/g5/protocol.json',
            'results/saqr_study/g5_o1t/protocol.json', 'results/saqr_study/col/pilot/protocol.json']


def main():
    gp, sp = verify_frozen()
    done = {}
    gate = []
    for c, js in jobs(gp, sp, meshes=[4, 8, 16, 32]):
        for j in js:
            f = ROOT / j['dir'] / 'result.json'
            if not f.exists():
                continue
            try:
                r = json.loads(f.read_text())
            except Exception:
                continue                    # half-written receipt: let Actions redo it
            if r['qos']['integrity_errors'] != 0:
                continue
            done[j['dir']] = r['trace_sha256']
            gate.append((c, j, r))
    # Reproduction gate: cheap held-out runs already completed locally, both binaries, every route,
    # both modes, every traffic case (k = 4 and 8, light loads), plus trace-only checks at k = 16.
    rng = random.Random(20261109)
    pick = []
    for stage in ('g4', 'src'):
        for k in (4, 8):
            pool = [x for x in gate if x[1]['stage'] == stage and x[0]['k'] == k and x[0]['index'] <= 3]
            per = {}
            for x in pool:
                per.setdefault((x[0]['traffic'], x[1]['name'], x[1]['mode']), []).append(x)
            keys = sorted(per)
            rng.shuffle(keys)
            want = 24 if stage == 'g4' else 8
            pick += [rng.choice(per[key]) for key in keys[:want]]
    trace_checks = {}
    for c, j, r in gate:
        if c['k'] == 16 and c['traffic'] not in {t for t, _ in trace_checks.values()} and len(trace_checks) < 6:
            trace_checks[c['name']] = (c['traffic'], r['trace_sha256'])
    manifest = dict(created=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    runs=[dict(case=c, job=j, ref=f'gate/ref/{i}.json') for i, (c, j, r) in enumerate(pick)],
                    trace_checks=[dict(case=next(cc for cc in gp['cases'] if cc['name'] == n), trace_sha256=s)
                                  for n, (_, s) in trace_checks.items()])
    out = HERE / 'bundle.tar.gz'
    with tarfile.open(out, 'w:gz') as tar:
        for f in FILES + [f for f in OPTIONAL if (ROOT / f).exists()]:
            tar.add(ROOT / f, arcname=f)

        def put(name, data):
            ti = tarfile.TarInfo(name); b = data.encode(); ti.size = len(b); ti.mtime = int(time.time())
            tar.addfile(ti, io.BytesIO(b))
        put('ci_bundle/done.json', json.dumps(done, indent=0, sort_keys=True))
        put('ci_bundle/gate/manifest.json', json.dumps(manifest, indent=1))
        for i, (c, j, r) in enumerate(pick):
            put(f'ci_bundle/gate/ref/{i}.json', json.dumps(r))
    print(f'bundle {out.stat().st_size/1e6:.1f} MB: {len(done)} runs done locally, gate {len(pick)} runs + {len(trace_checks)} k16 trace checks')


if __name__ == '__main__':
    main()
