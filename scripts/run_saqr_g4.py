"""SAQR G4 held-out evaluation (docs/SAQR_SPEC_V2.md §18; design from CHR spec §7 G4).

Held-out seeds 201-205, never used for tuning. All six frozen traffic cases on
their frozen load grids (scripts/run_qos_grid.py), meshes k = 4, 8, 16, 32,
both scheduling modes (age = matched control, weighted = QoS). Fresh traces
from the frozen generator. Every route runs fresh on the SAQR binary.

The candidates and their parameters were frozen in §17 before this runner
existed. The protocol (variants, binary, sources, evaluator hash, criteria) is
written before the first run and must match on every resume. The meshes run in
tiers (--meshes); the protocol always covers the full matrix.
"""
import argparse
import concurrent.futures
import json
import traceback
from chr_common import ROOT, SAQR_STUDY, SAQR_BINARY, sha, run, trace

OUT=SAQR_STUDY/'g4'
SEEDS=[201,202,203,204,205]
MESHES=[4,8,16,32]
TRAFFIC=['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center']
MODES=['weighted','age']
# Frozen before held-out data (§17). name -> (routing algorithm, tuning env overrides)
VARIANTS={
    'xy':(               'xy',{}),
    'oefixed':(          'oefixed',{}),
    'dyad':(             'dyad',{}),
    'topsis':(           'topsis',{}),
    'duato':(            'duato',{}),
    'westfirst':(        'westfirst',{}),
    'saqr_o1t_both':(    'saqr_nogate',{'NOC_SAQR_O1TURN_MASK':3}),   # primary candidate
    'saqr_nogate_crit':( 'saqr_nogate',{'NOC_SAQR_CLASS_MASK':1}),    # uniform-closest candidate
}
CANDIDATES=['saqr_o1t_both','saqr_nogate_crit']
SOURCES=['algorithms/saqr/routing.hpp','simulators/booksim_saqr/saqr_routes.cpp','scripts/setup_saqr.py',
         'scripts/chr_common.py','scripts/qos_common.py','scripts/run_saqr_g4.py','scripts/evaluate_saqr_g4.py']

def cases():
    for k in MESHES:
        for traffic in TRAFFIC:
            grid=[.1,.25,.5,.7,.85,1,1.15,1.5,2] if traffic.startswith('hotspot') else [.02,.05,.1,.2,.3,.4,.6,.8,1]
            for i,v in enumerate(grid):
                load=float(f'{v/(.2*k*k+.8) if traffic.startswith("hotspot") else v*4/k:.12g}')
                for seed in SEEDS:
                    yield dict(k=k,traffic=traffic,index=i,load=load,seed=seed,name=f'k{k}_{traffic}_l{i}_s{seed}')

def protocol():
    cs=list(cases())
    return dict(stage='saqr_g4_heldout',seeds=SEEDS,meshes=MESHES,traffic=TRAFFIC,modes=MODES,cases=cs,
                variants={k:[v[0],v[1]] for k,v in VARIANTS.items()},candidates=CANDIDATES,
                expected_runs=len(cs)*len(VARIANTS)*len(MODES),warmup=5000,measurement=20000,
                saqr_binary_sha256=sha(SAQR_BINARY),source_sha256={s:sha(ROOT/s) for s in SOURCES},
                r0_receipt_sha256=sha(SAQR_STUDY/'r0/r0_receipt.json'),
                frozen_in='docs/SAQR_SPEC_V2.md §17 (candidates) and §18 (protocol)',
                criteria='CHR_OE_CANDIDATE_SPEC.md §8 margins plus SAQR_SPEC_V2.md §9 additions, as implemented in scripts/evaluate_saqr_g4.py (hash above)')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8)
    p.add_argument('--meshes',type=int,nargs='+',default=MESHES); a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    r0=json.loads((SAQR_STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['binary_sha256']==sha(SAQR_BINARY),'R0 must pass for the current SAQR binary'
    proto=protocol(); pp=OUT/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==proto,'G4 protocol mismatch: binary, sources or design changed'
    else: pp.write_text(json.dumps(proto,indent=2)+'\n')
    # Largest loads first inside each mesh so long runs do not trail at the end.
    todo=sorted([c for c in proto['cases'] if c['k'] in a.meshes],key=lambda c:(c['k'],-c['index'],c['traffic'],c['seed']))
    jobs=[(c,mode,name) for c in todo for mode in MODES for name in VARIANTS]

    def work(job):
        c,mode,name=job; alg,env=VARIANTS[name]
        folder=OUT/'cases'/c['name']; demand=folder/'demand.txt'; assert demand.exists()
        d=folder/f'{mode}_{name}'; receipt=d/'result.json'
        if receipt.exists():
            r=json.loads(receipt.read_text())
            assert r['binary_sha256']==proto['saqr_binary_sha256'] and r['trace_sha256']==sha(demand)
            assert r['mode']==mode and r['chr_env']=={k:v for k,v in env.items()}
        else: r=run(d,demand,c['k'],alg,c['seed'],mode,chr_env=env,binary=SAQR_BINARY)
        if r['qos']['integrity_errors']!=0: raise RuntimeError(f'integrity errors: {r["qos"]["integrity_errors"]}')
        return 1

    # Trace generation is per case; serialize it so two jobs never write the same demand file.
    for c in todo:
        folder=OUT/'cases'/c['name']; folder.mkdir(parents=True,exist_ok=True); demand=folder/'demand.txt'
        if not demand.exists():
            tmp=folder/'demand.tmp'; trace(tmp,c['k'],c['load'],c['seed'],c['traffic']); tmp.replace(demand)
    print(f'traces ready: {len(todo)} cases, {len(jobs)} runs (meshes {a.meshes})',flush=True)

    done=0; failures=[]
    prev=json.loads((OUT/'progress.json').read_text()) if (OUT/'progress.json').exists() else {}
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        fut={pool.submit(work,j):j for j in jobs}
        for f in concurrent.futures.as_completed(fut):
            c,mode,name=fut[f]
            try: done+=f.result()
            except Exception as exc:
                failures.append(dict(case=c['name'],mode=mode,route=name,error=repr(exc),trace=traceback.format_exc()[-800:]))
                print('FAILED',c['name'],mode,name,repr(exc),flush=True)
            if done%50==0 or failures and failures[-1]['case']==c['name']:
                print(f'progress {done}/{len(jobs)}',flush=True)
            prog=dict(prev,**{f'k{"_".join(map(str,a.meshes))}':dict(expected=len(jobs),completed=done,failures=failures)},
                      expected_runs_total=proto['expected_runs'])
            t=OUT/'progress.tmp'; t.write_text(json.dumps(prog,indent=2)+'\n'); t.replace(OUT/'progress.json')
    print(f'G4 TIER {a.meshes}: {done}/{len(jobs)} runs, {len(failures)} failures',flush=True)

if __name__=='__main__': main()
