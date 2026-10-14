"""Complete BookSim grid for the presentation, reusing compatible measured cases."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
from run_experiments import ROOT,write_rows,execution_profile

SIZES=[4,8,16,32]
LOADS=[i/10 for i in range(1,11)]
TRAFFIC=['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center']
SEEDS=[1,2,3]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--retry-failed',action='store_true',help='Retry only failed cases from a finished full-grid manifest')
    a=p.parse_args()
    output=ROOT/'results/primary_grid'; output.mkdir(parents=True,exist_ok=True)
    cases=list(itertools.product(SIZES,LOADS,TRAFFIC,SEEDS))
    rows=[]
    if a.retry_failed:
        previous=json.loads((output/'manifest.json').read_text())
        if previous['actual_rows']!=2160: p.error('Use a normal resume for an interrupted or incomplete grid')
        cases=[tuple(c) for c in previous['failed_cases']]
        rows=json.loads((output/'metrics.json').read_text())
        failed_keys=set(cases)
        rows=[r for r in rows if (r['mesh_k'],r['offered_flits_per_node_cycle'],r['traffic'],r['seed']) not in failed_keys]
    sources=['workloads','transpose_load','traffic_scaling']
    def work(case):
        k,load,traffic,seed=case; name=f'k{k}_{traffic}_l{load}_s{seed}'
        dest=output/'cases'/name; raw=dest/'raw'; raw.mkdir(parents=True,exist_ok=True)
        for alg in ['xy','dyad','topsis']:
            stem=f'booksim_{alg}_k{k}_{traffic}_l{load}_s{seed}'
            if (raw/(stem+'.json')).exists(): continue
            for study in sources:
                source=ROOT/'results'/study/'cases'/name/'raw'; path=source/(stem+'.json')
                if not path.exists(): continue
                row=json.loads(path.read_text())
                if row['status']!='ok' or row['warmup_cycles']!=1000 or row['measurement_cycles']!=3000: continue
                if row.get('execution_profile')!=execution_profile('booksim',traffic): continue
                for file in source.glob(stem+'.*'): shutil.copyfile(file,raw/file.name)
                row['reused_from']=str(path.relative_to(ROOT)); (raw/(stem+'.json')).write_text(json.dumps(row,indent=2)+'\n')
                break
        command=[sys.executable,str(ROOT/'scripts/run_experiments.py'),'--simulators','booksim',
                 '--sizes',str(k),'--loads',str(load),'--traffic',traffic,'--seeds',str(seed),
                 '--warmup','1000','--cycles','3000','--output',str(dest),'--resume']
        with (dest/'runner.log').open('w') as f:
            result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
        path=dest/'metrics.json'
        return case,result.returncode,json.loads(path.read_text()) if path.exists() else []
    failed=[]
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for future in as_completed([pool.submit(work,c) for c in cases]):
            case,code,new=future.result(); rows.extend(new)
            if code: failed.append(case)
            write_rows(output,rows)
            if len(rows)%30==0 or code: print(f'{len(rows)}/2160 runs; latest {case}; failed cases {len(failed)}',flush=True)
    manifests=list((ROOT/'algorithms').rglob('*.hpp'))+list((ROOT/'simulators').rglob('*.*'))
    manifest=dict(study='Primary BookSim full-load grid',sizes=SIZES,loads=LOADS,traffic=TRAFFIC,seeds=SEEDS,
                  warmup_cycles=1000,measurement_cycles=3000,expected_rows=2160,actual_rows=len(rows),failed_cases=failed,
                  concurrent_workers=a.jobs,runtime_is_diagnostic_only=True,
                  sources_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in manifests})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if failed or len(rows)!=2160: raise SystemExit('Incomplete primary grid; rerun with resume after inspecting logs.')

if __name__=='__main__': main()
