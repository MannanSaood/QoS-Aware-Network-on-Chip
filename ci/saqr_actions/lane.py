"""One Actions lane of a wave: run this lane's share of the remaining frozen held-out runs.

Remaining = every run of both frozen matrices (meshes 8, 16, 32) minus runs completed
locally (bundle done.json) minus runs already committed to the results branch.
Cases (all 18 runs of one trace) are dealt to lanes round-robin: smaller meshes first,
longest loads first within a mesh.
Runs use the unchanged chr_common.run with exactly the runners' arguments.

Checkpointing: new runs start only before --launch-hours; at --stop-hours any run still
going is killed (it simply reruns next wave). Each finished run's result.json is kept
and packed for upload, so nothing completed is ever lost to the 6-hour job limit.
"""
import argparse
import concurrent.futures
import json
import subprocess
import tarfile
import threading
import time
import traceback
from pathlib import Path

from common import ROOT, demand_path, jobs, verify_frozen
from chr_common import run, sha, trace


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--lane', type=int, required=True); p.add_argument('--lanes', type=int, required=True)
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--launch-hours', type=float, default=5.0); p.add_argument('--stop-hours', type=float, default=5.5)
    p.add_argument('--committed', required=True, help='file listing result.json paths on the results branch')
    p.add_argument('--traces', required=True, help='traces.json from the results branch (case -> sha)')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    t0 = time.time(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    gp, sp = verify_frozen()
    done_local = json.loads((ROOT / 'ci_bundle' / 'done.json').read_text())
    committed = {l.strip()[:-len('/result.json')] for l in Path(a.committed).read_text().splitlines() if l.strip().endswith('/result.json')}
    known = json.loads(Path(a.traces).read_text()) if Path(a.traces).exists() else {}
    for d, s in done_local.items():                 # trace shas of local receipts, by case
        known.setdefault(Path(d).parent.name, s)

    todo = []
    for c, js in jobs(gp, sp):
        rest = [j for j in js if j['dir'] not in done_local and j['dir'] not in committed]
        if rest:
            todo.append((c, rest))
    # Smaller meshes first (16x16 finishes before 32x32 starts), longest loads first within a mesh.
    todo.sort(key=lambda x: (x[0]['k'], -x[0]['index'], x[0]['traffic'], x[0]['seed']))
    mine = [x for i, x in enumerate(todo) if i % a.lanes == a.lane]
    print(f'lane {a.lane}/{a.lanes}: {len(todo)} cases remain overall, {len(mine)} here ({sum(len(r) for _, r in mine)} runs)', flush=True)

    rep = dict(lane=a.lane, completed=[], failures=[], interrupted=[], traces={}, trace_mismatch=[], not_started=0)
    stop = threading.Event(); lock = threading.Lock(); slots = threading.Semaphore(a.jobs)

    def watchdog():
        while not stop.wait(30):
            if time.time() - t0 > a.stop_hours * 3600:
                stop.set()
        subprocess.run(['pkill', '-f', 'booksim2_saqr'], check=False)   # runs still going rerun next wave
    threading.Thread(target=watchdog, daemon=True).start()

    def work(c, j, demand):
        try:
            d = ROOT / j['dir']
            r = run(d, demand, c['k'], j['alg'], c['seed'], j['mode'], chr_env=j['env'], binary=ROOT / j['binary'])
            with lock:
                if r['qos']['integrity_errors'] != 0:
                    rep['failures'].append(dict(dir=j['dir'], error=f"integrity errors {r['qos']['integrity_errors']}"))
                else:
                    rep['completed'].append(dict(dir=j['dir'], wall=r['wall_seconds']))
        except Exception as exc:
            with lock:
                if stop.is_set():
                    rep['interrupted'].append(j['dir'])
                else:
                    rep['failures'].append(dict(dir=j['dir'], error=repr(exc), trace=traceback.format_exc()[-600:]))
        finally:
            slots.release()

    pool = concurrent.futures.ThreadPoolExecutor(a.jobs); futs = []
    for c, rest in mine:
        if time.time() - t0 > a.launch_hours * 3600 or stop.is_set():
            rep['not_started'] += len(rest); continue
        demand = demand_path(c); demand.parent.mkdir(parents=True, exist_ok=True)
        if not demand.exists():
            trace(demand.parent / 'demand.tmp', c['k'], c['load'], c['seed'], c['traffic']); (demand.parent / 'demand.tmp').replace(demand)
        s = sha(demand); rep['traces'][c['name']] = s
        if c['name'] in known and known[c['name']] != s:
            rep['trace_mismatch'].append(c['name']); continue      # never run on a trace that differs from earlier receipts
        for j in rest:
            while not slots.acquire(timeout=10):
                if stop.is_set():
                    break
            if stop.is_set() or time.time() - t0 > a.launch_hours * 3600:
                rep['not_started'] += 1; continue
            futs.append(pool.submit(work, c, j, demand))
    pool.shutdown(wait=True); stop.set()

    with tarfile.open(out / f'lane{a.lane}.tar.gz', 'w:gz') as tar:
        for x in rep['completed']:
            tar.add(ROOT / x['dir'] / 'result.json', arcname=x['dir'] + '/result.json')
    rep['hours'] = (time.time() - t0) / 3600
    (out / f'lane{a.lane}.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(f"lane {a.lane}: {len(rep['completed'])} completed, {len(rep['failures'])} failed, {len(rep['interrupted'])} interrupted, "
          f"{rep['not_started']} not started, {len(rep['trace_mismatch'])} trace mismatches, {rep['hours']:.2f} h", flush=True)


if __name__ == '__main__':
    main()
