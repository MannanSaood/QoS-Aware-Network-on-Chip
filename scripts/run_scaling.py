"""Complete size-scaling study with bounded concurrent simulator processes.

Workers are ordinary subprocess jobs, not AI agents. Wall times under concurrency
are diagnostic only. Use --jobs 1 for a dedicated host runtime study.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
from run_experiments import ROOT, write_rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--jobs",type=int,default=4)
    p.add_argument("--simulators",nargs="+",choices=["booksim","ns2"],default=["booksim","ns2"])
    p.add_argument("--sizes",type=int,nargs="+",default=[4,8,16,32])
    p.add_argument("--loads",type=float,nargs="+",default=[.05,.3])
    p.add_argument("--seeds",type=int,nargs="+",default=[1,2,3])
    p.add_argument("--traffic",nargs="+",default=["uniform","hotspot"])
    p.add_argument("--cycles",type=int,default=1000)
    p.add_argument("--warmup",type=int,default=500)
    p.add_argument("--timeout-seconds",type=int,default=900)
    p.add_argument("--output",type=Path,default=ROOT/"results/scaling")
    a=p.parse_args(); a.output=a.output.resolve(); a.output.mkdir(parents=True,exist_ok=True)
    scenarios=list(itertools.product(a.sizes,a.loads,a.seeds,a.traffic))
    def work(case):
        k,load,seed,traffic=case
        destination=a.output/"cases"/f"k{k}_{traffic}_l{load}_s{seed}"
        destination.mkdir(parents=True,exist_ok=True)
        command=[sys.executable,str(ROOT/"scripts/run_experiments.py"),"--sizes",str(k),"--loads",str(load),
                 "--seeds",str(seed),"--traffic",traffic,"--cycles",str(a.cycles),"--warmup",str(a.warmup),
                 "--output",str(destination),"--resume","--timeout-seconds",str(a.timeout_seconds),"--simulators",*a.simulators]
        with (destination/"runner.log").open("w") as log:
            completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        path=destination/"metrics.json"
        return case,completed.returncode,json.loads(path.read_text()) if path.exists() else []
    rows=[]; failures=[]
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for task in as_completed([pool.submit(work,c) for c in scenarios]):
            case,code,result=task.result(); rows.extend(result)
            if code: failures.append(case)
            write_rows(a.output,rows)
            print(f"Completed {case}: {len(result)} rows, exit {code}; total {len(rows)}",flush=True)
    sources=list((ROOT/"algorithms").rglob("*.hpp"))+list((ROOT/"simulators").rglob("*.*"))
    manifest=dict(study="finite-window size scaling",sizes=a.sizes,loads=a.loads,seeds=a.seeds,traffic=a.traffic,
                  warmup_cycles=a.warmup,measurement_cycles=a.cycles,occupancy_sample_stride_cycles=10,
                  concurrent_workers=a.jobs,runtime_is_diagnostic_only=a.jobs>1,
                  simulators=a.simulators,expected_rows=len(scenarios)*len(a.simulators)*3,actual_rows=len(rows),failed_cases=failures,
                  sources_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources})
    (a.output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    if failures or len(rows)!=len(scenarios)*len(a.simulators)*3: raise SystemExit("Incomplete cases; see per-case runner.log")

if __name__=="__main__": main()
