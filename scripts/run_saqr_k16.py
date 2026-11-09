"""SAQR 16x16 frontier stage (docs/SAQR_SPEC_V2.md §13). Weighted mode, tuning seeds 101-103.

Scale check for the three 8x8 frontier variants against XY, OE-fixed,
DyAD-OE, TOPSIS-OE and Duato. Same traffic/index/seed scheme as the 8x8
pilots (fresh 16x16 traces from the frozen generator). Every route is run
fresh with the SAQR binary; nothing is reused.

Anchor: R0 covered k=4,8 only, so before any new run the SAQR binary must
reproduce frozen 16x16 receipts exactly (xy/dyad/topsis, seed 1, three
traffics). The protocol is written before any run and must match on rerun.
These are tuning seeds; no acceptance claim is made from this stage.
"""
import argparse
import concurrent.futures
import json
from chr_common import ROOT, SAQR_STUDY, SAQR_BINARY, sha, run, trace

K=16
FROZEN=ROOT/'results/qos_comparison/cases'
# name -> (routing algorithm, tuning env overrides)
VARIANTS={
    'xy':(               'xy',{}),
    'oefixed':(          'oefixed',{}),
    'dyad':(             'dyad',{}),
    'topsis':(           'topsis',{}),
    'duato':(            'duato',{}),
    'saqr':(             'saqr',{}),
    'saqr_nogate':(      'saqr_nogate',{}),
    'saqr_nogate_crit':( 'saqr_nogate',{'NOC_SAQR_CLASS_MASK':1}),
}
TRAFFIC=['uniform','transpose','hotspot_center']
SEEDS=[101,102,103]
INDICES={'uniform':[4,5,6,7,8],'transpose':[4,5,6,7,8],'hotspot_center':[3,4,5,6,7]}
ANCHOR=[f'k16_{t}_l6_s1' for t in TRAFFIC]
ANCHOR_ROUTES=['xy','dyad','topsis']

def load(k,traffic,i):
    grid=[.1,.25,.5,.7,.85,1,1.15,1.5,2] if traffic.startswith('hotspot') else [.02,.05,.1,.2,.3,.4,.6,.8,1]
    v=grid[i]
    return float(f'{v/(.2*k*k+.8) if traffic.startswith("hotspot") else v*4/k:.12g}')

def cases():
    for traffic in TRAFFIC:
        for i in INDICES[traffic]:
            for seed in SEEDS:
                yield dict(k=K,traffic=traffic,index=i,load=load(K,traffic,i),seed=seed,name=f'k{K}_{traffic}_l{i}_s{seed}')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); p.add_argument('--only',default=None,help='run one case name (smoke)'); a=p.parse_args()
    out=SAQR_STUDY/'stage_k16'; out.mkdir(parents=True,exist_ok=True)
    r0=json.loads((SAQR_STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['binary_sha256']==sha(SAQR_BINARY),'R0 must pass for the current SAQR binary'
    cs=list(cases())
    protocol=dict(stage='saqr_stage_k16',mode='weighted',cases=cs,variants={k:[v[0],v[1]] for k,v in VARIANTS.items()},
                  anchor_cases=ANCHOR,anchor_routes=ANCHOR_ROUTES,saqr_binary_sha256=sha(SAQR_BINARY),
                  runner_sha256=sha(__file__),warmup=5000,measurement=20000,expected_runs=len(cs)*len(VARIANTS))
    pp=out/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol,'Stage protocol mismatch'
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')

    # 1. Anchor: reproduce frozen 16x16 receipts exactly.
    def anchor(job):
        name,route=job
        frozen=json.loads((FROZEN/name/f'weighted_{route}'/'result.json').read_text())
        demand=FROZEN/name/'demand.txt'; assert sha(demand)==frozen['trace_sha256']
        d=out/'anchor'/name/route
        new=json.loads((d/'result.json').read_text()) if (d/'result.json').exists() else run(d,demand,K,route,frozen['seed'],'weighted',binary=SAQR_BINARY)
        return dict(case=name,route=route,identical=new['aggregate']==frozen['aggregate'] and new['qos']==frozen['qos'] and new['config_sha256']==frozen['config_sha256'])
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        xc=list(pool.map(anchor,[(n,r) for n in ANCHOR for r in ANCHOR_ROUTES]))
    (out/'anchor.json').write_text(json.dumps(xc,indent=2)+'\n')
    assert all(x['identical'] for x in xc),f'Anchor failed: {[x for x in xc if not x["identical"]]}'
    print(f'anchor: {len(xc)}/{len(xc)} identical to frozen 16x16 receipts',flush=True)

    # 2. Stage runs.
    def work(c):
        folder=out/'cases'/c['name']; folder.mkdir(parents=True,exist_ok=True)
        demand=folder/'demand.txt'
        if not demand.exists():
            tmp=folder/'demand.tmp'; trace(tmp,c['k'],c['load'],c['seed'],c['traffic']); tmp.replace(demand)
        rows=[]
        for name,(alg,env) in VARIANTS.items():
            d=folder/f'weighted_{name}'; receipt=d/'result.json'
            if receipt.exists():
                r=json.loads(receipt.read_text())
                assert r['binary_sha256']==protocol['saqr_binary_sha256'] and r['trace_sha256']==sha(demand)
            else: r=run(d,demand,c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
            assert r['qos']['integrity_errors']==0
            rows.append(name)
        print(c['name'],'ok',flush=True)
        return rows
    todo=[c for c in cs if a.only is None or c['name']==a.only]
    done=0; failures=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures={pool.submit(work,c):c for c in todo}
        for f in concurrent.futures.as_completed(futures):
            try: done+=len(f.result())
            except Exception as exc: failures.append(dict(case=futures[f]['name'],error=repr(exc))); print('FAILED',futures[f]['name'],repr(exc),flush=True)
            prog=dict(expected_runs=protocol['expected_runs'],completed_runs=done,failed_cases=failures,complete=done==protocol['expected_runs'] and not failures)
            t=out/'progress.tmp'; t.write_text(json.dumps(prog,indent=2)+'\n'); t.replace(out/'progress.json')
    assert not failures
    print(f'SAQR 16x16 STAGE: {done} runs done',flush=True)

if __name__=='__main__': main()
