"""CHR-OE D0 + tuning pilot (docs/CHR_OE_CANDIDATE_SPEC.md section 7, stage 3a/3b).

Weighted mode only, starting parameters only (no tuning in this run).
Fresh trace seeds 101-103 so the seed 1-3 showcase traces are never used.
The protocol is written before any run. A rerun must match it exactly.
"""
import argparse
import concurrent.futures
import json
from chr_common import ROOT, STUDY, CHR_BINARY, sha, run, trace

ROUTES=['xy','oefixed','dyad','topsis','chr_cls','chr_hyst','chr_nofv','chr']
TRAFFIC=['uniform','transpose','hotspot_center']
SEEDS=[101,102,103]
# Frozen-grid indices covering the transition region (declared before running).
INDICES={'uniform':[4,5,6,7,8],'transpose':[4,5,6,7,8],'hotspot_center':[3,4,5,6,7]}
REPEAT_ROUTE='chr'   # determinism check: rerun on the first case of each traffic

def load(k,traffic,i):
    grid=[.1,.25,.5,.7,.85,1,1.15,1.5,2] if traffic.startswith('hotspot') else [.02,.05,.1,.2,.3,.4,.6,.8,1]
    v=grid[i]
    return float(f'{v/(.2*k*k+.8) if traffic.startswith("hotspot") else v*4/k:.12g}')

def cases(k):
    for traffic in TRAFFIC:
        for i in INDICES[traffic]:
            for seed in SEEDS:
                yield dict(k=k,traffic=traffic,index=i,load=load(k,traffic,i),seed=seed,name=f'k{k}_{traffic}_l{i}_s{seed}')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--k',type=int,default=8); p.add_argument('--jobs',type=int,default=8); a=p.parse_args()
    out=STUDY/f'pilot_k{a.k}'; out.mkdir(parents=True,exist_ok=True)
    r0=json.loads((STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['chr_binary_sha256']==sha(CHR_BINARY),'R0 must pass for the current CHR binary'
    cs=list(cases(a.k))
    protocol=dict(stage=f'pilot_k{a.k}',mode='weighted',routes=ROUTES,cases=cs,expected_runs=len(cs)*len(ROUTES),
                  parameters='spec section 3.1 starting values with amendment A1; no overrides',
                  chr_binary_sha256=sha(CHR_BINARY),runner_sha256=sha(__file__),
                  warmup=5000,measurement=20000,determinism_repeat_route=REPEAT_ROUTE)
    pp=out/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol,'Pilot protocol mismatch'
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')
    def work(c):
        folder=out/'cases'/c['name']; folder.mkdir(parents=True,exist_ok=True)
        demand=folder/'demand.txt'
        if not demand.exists():
            tmp=folder/'demand.tmp'; trace(tmp,c['k'],c['load'],c['seed'],c['traffic']); tmp.replace(demand)
        rows=[]
        for route in ROUTES:
            d=folder/f'weighted_{route}'; receipt=d/'result.json'
            if receipt.exists():
                r=json.loads(receipt.read_text())
                assert r['binary_sha256']==protocol['chr_binary_sha256'] and r['trace_sha256']==sha(demand)
            else: r=run(d,demand,c['k'],route,c['seed'],'weighted')
            assert r['qos']['integrity_errors']==0
            rows.append(dict(case=c,route=route))
        print(c['name'],'ok',flush=True)
        return rows
    done=0; failures=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures={pool.submit(work,c):c for c in cs}
        for f in concurrent.futures.as_completed(futures):
            try: done+=len(f.result())
            except Exception as exc: failures.append(dict(case=futures[f]['name'],error=repr(exc))); print('FAILED',futures[f]['name'],repr(exc),flush=True)
            prog=dict(expected_runs=protocol['expected_runs'],completed_runs=done,failed_cases=failures,
                      complete=done==protocol['expected_runs'] and not failures)
            t=out/'progress.tmp'; t.write_text(json.dumps(prog,indent=2)+'\n'); t.replace(out/'progress.json')
    # Determinism: identical trace + binary must give identical metrics.
    det=[]
    for traffic in TRAFFIC:
        c=next(x for x in cs if x['traffic']==traffic)
        folder=out/'cases'/c['name']
        first=json.loads((folder/f'weighted_{REPEAT_ROUTE}'/'result.json').read_text())
        again=run(out/'repeat'/c['name'],folder/'demand.txt',c['k'],REPEAT_ROUTE,c['seed'],'weighted')
        det.append(dict(case=c['name'],identical=all(first[x]==again[x] for x in ('aggregate','qos','chr'))))
    (out/'determinism.json').write_text(json.dumps(det,indent=2)+'\n')
    print('determinism',det,flush=True)
    assert not failures and all(d['identical'] for d in det)
    print(f'PILOT k={a.k} COMPLETE: {done} runs',flush=True)

if __name__=='__main__': main()
