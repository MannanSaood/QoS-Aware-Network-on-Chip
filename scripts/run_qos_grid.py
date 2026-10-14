"""Frozen two-class showcase and matched-control sweep with exact demand replay."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import time
from qos_common import ROOT, BINARY, sha, trace, run

OUT=ROOT/'results/qos_comparison'

def matrix():
    for k in [4,8,16,32]:
        for traffic in ['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center']:
            loads=([.1,.25,.5,.7,.85,1,1.15,1.5,2] if traffic.startswith('hotspot') else [.02,.05,.1,.2,.3,.4,.6,.8,1])
            loads=[float(f'{v/(.2*k*k+.8) if traffic.startswith("hotspot") else v*4/k:.12g}') for v in loads]
            for i,load in enumerate(loads):
                for seed in [1,2,3]:
                    yield dict(k=k,traffic=traffic,index=i,load=load,seed=seed,name=f'k{k}_{traffic}_l{i}_s{seed}')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=2); a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    validation=json.loads((ROOT/'results/qos_validation/validation.json').read_text())
    assert validation['status']=='pass' and validation['binary_sha256']==sha(BINARY),'Validate current binary first'
    cases=list(matrix())
    sources=[*sorted((ROOT/'simulators/booksim_qos').glob('*.*')),ROOT/'scripts/qos_common.py',Path(__file__),
             ROOT/'scripts/setup_qos.py',ROOT/'scripts/validate_qos.py']
    protocol=dict(cases=cases,expected_runs=3888,modes=['age','weighted'],algorithms=['xy','dyad','topsis'],
                  warmup=5000,measurement=20000,packet_flits=5,critical_fraction=.25,weights=[3,1],vcs=4,depth=8,
                  binary_sha256=sha(BINARY),source_sha256={str(f.relative_to(ROOT)):sha(f) for f in sources},
                  validation_sha256=sha(ROOT/'results/qos_validation/validation.json'),
                  definition='Identical demand trace for all six algorithm/policy combinations. QoS is weighted class service; age is matched control. Finite windows, no drain.')
    pp=OUT/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol,'Frozen QoS protocol mismatch'
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')
    results=[]; failures=[]
    def work(case):
        folder=OUT/'cases'/case['name']; folder.mkdir(parents=True,exist_ok=True)
        demand=folder/'demand.txt'
        if not demand.exists(): trace(demand,case['k'],case['load'],case['seed'],case['traffic'])
        digest=sha(demand); rows=[]
        for mode in ['age','weighted']:
            for algorithm in ['xy','dyad','topsis']:
                directory=folder/(mode+'_'+algorithm); receipt=directory/'result.json'
                if receipt.exists():
                    result=json.loads(receipt.read_text())
                    assert result['binary_sha256']==protocol['binary_sha256'] and result['trace_sha256']==digest
                    assert result['mode']==mode and result['algorithm']==algorithm
                else: result=run(directory,demand,case['k'],algorithm,case['seed'],mode)
                rows.append(dict(case=case,result=result))
                print(case['name'],mode,algorithm,'ok',flush=True)
        return rows
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        pending={pool.submit(work,c):c for c in cases}
        for future in concurrent.futures.as_completed(pending):
            case=pending[future]
            try: results.extend(future.result())
            except Exception as exc:
                failures.append(dict(case=case['name'],error=repr(exc)))
                print('FAILED',case['name'],repr(exc),flush=True)
            progress=dict(expected_runs=3888,completed_runs=len(results),failed_cases=failures,complete=len(results)==3888 and not failures)
            tmp=OUT/'progress.tmp'; tmp.write_text(json.dumps(progress,indent=2)+'\n'); tmp.replace(OUT/'progress.json')
    (OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    assert len(results)==3888 and not failures,failures
    assert sha(BINARY)==protocol['binary_sha256']
    print('QoS sweep COMPLETE: 3888/3888',flush=True)

if __name__=='__main__': main()
