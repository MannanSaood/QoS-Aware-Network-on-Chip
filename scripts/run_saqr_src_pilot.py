"""SAQR-SC tuning pilot (docs/SAQR_SPEC_V2.md §19). Tuning seeds 101-103 only.

k = 8: the CHR-pilot traces (uniform, transpose, hotspot_center; five loads each).
SAQR-SC variants run fresh on the SAQR-SC binary. Baselines are read from
their existing tuning receipts (same traces, cross-checked in earlier rounds).
k = 4: fresh tuning traces with the same traffic/index/seed scheme; every route
runs fresh (baselines on the G4 SAQR binary, SAQR-SC variants on the SAQR-SC binary).

Variant grid and selection rule are fixed here, before any SAQR-SC run:
  sc_128_64 (default), sc_96_48, sc_192_96: on/off thresholds (x/256), M = 4, shift = 4.
  sc_never (on = 256, unreachable): every packet deterministic; must equal XY
    (checks the "exact XY when calm" claim; not a candidate).
  Selection: among variants whose uniform throughput lower bound vs XY is > -3%
  at every uniform load at both k (C1 rule on tuning data), pick the highest mean
  transpose throughput over both k; ties (< 0.5 %) go to sc_128_64.
"""
import argparse
import concurrent.futures
import json
from chr_common import STUDY, SAQR_BINARY
from saqr_src_common import SAQR_STUDY, SRC_BINARY, SRC_STUDY, sha, run, trace

OUT=SRC_STUDY/'pilot'
SC={'sc_128_64':{'NOC_SAQR_SRC_ON':128,'NOC_SAQR_SRC_OFF':64},
    'sc_96_48':{'NOC_SAQR_SRC_ON':96,'NOC_SAQR_SRC_OFF':48},
    'sc_192_96':{'NOC_SAQR_SRC_ON':192,'NOC_SAQR_SRC_OFF':96},
    'sc_never':{'NOC_SAQR_SRC_ON':256,'NOC_SAQR_SRC_OFF':256}}
BASE={'xy':('xy',{}),'oefixed':('oefixed',{}),'dyad':('dyad',{}),'topsis':('topsis',{}),'duato':('duato',{}),
      'westfirst':('westfirst',{}),'saqr_o1t_both':('saqr_nogate',{'NOC_SAQR_O1TURN_MASK':3}),
      'saqr_nogate_crit':('saqr_nogate',{'NOC_SAQR_CLASS_MASK':1})}
# k = 8 baseline receipts: route -> results directory holding cases/<name>/weighted_<route>/result.json
K8_REF={'xy':STUDY/'pilot_k8','oefixed':STUDY/'pilot_k8','dyad':STUDY/'pilot_k8','topsis':STUDY/'pilot_k8',
        'duato':SAQR_STUDY/'pilot_k8','westfirst':SAQR_STUDY/'pilot_k8','saqr_o1t_both':SAQR_STUDY/'pilot_k8_r7',
        'saqr_nogate_crit':SAQR_STUDY/'pilot_k8_r3'}
TRAFFIC=['uniform','transpose','hotspot_center']; SEEDS=[101,102,103]
INDICES={'uniform':[4,5,6,7,8],'transpose':[4,5,6,7,8],'hotspot_center':[3,4,5,6,7]}

def load(k,traffic,i):
    grid=[.1,.25,.5,.7,.85,1,1.15,1.5,2] if traffic.startswith('hotspot') else [.02,.05,.1,.2,.3,.4,.6,.8,1]
    v=grid[i]; return float(f'{v/(.2*k*k+.8) if traffic.startswith("hotspot") else v*4/k:.12g}')

def k4_cases():
    return [dict(k=4,traffic=t,index=i,load=load(4,t,i),seed=s,name=f'k4_{t}_l{i}_s{s}') for t in TRAFFIC for i in INDICES[t] for s in SEEDS]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    gate=json.loads((SRC_STUDY/'r0/r0_receipt.json').read_text())
    assert gate['status']=='pass' and gate['binary_sha256']==sha(SRC_BINARY),'R0+X1 must pass for the SAQR-SC binary'
    k8=json.loads((STUDY/'pilot_k8/protocol.json').read_text())['cases']; k4=k4_cases()
    proto=dict(stage='saqr_src_pilot',k8_cases=k8,k4_cases=k4,sc_variants=SC,baselines={k:[v[0],v[1]] for k,v in BASE.items()},
               k8_reference_dirs={k:str(v.relative_to(SAQR_STUDY.parent)) for k,v in K8_REF.items()},
               src_binary_sha256=sha(SRC_BINARY),saqr_binary_sha256=sha(SAQR_BINARY),runner_sha256=sha(__file__))
    pp=OUT/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==proto,'pilot protocol mismatch'
    else: pp.write_text(json.dumps(proto,indent=2)+'\n')
    for c in k4:
        f=OUT/'cases'/c['name']; f.mkdir(parents=True,exist_ok=True); d=f/'demand.txt'
        if not d.exists(): tmp=f/'demand.tmp'; trace(tmp,4,c['load'],c['seed'],c['traffic']); tmp.replace(d)
    jobs=[(c,n,'sc') for c in k8+k4 for n in SC]+[(c,n,'base') for c in k4 for n in BASE]
    def work(job):
        c,name,kind=job
        demand=(STUDY/'pilot_k8' if c['k']==8 else OUT)/'cases'/c['name']/'demand.txt'
        d=OUT/'cases'/c['name']/f'weighted_{name}'
        if (d/'result.json').exists(): return 1
        alg,env,binary=(('saqr_nogate',SC[name],SRC_BINARY) if kind=='sc' else (*BASE[name],SAQR_BINARY))
        r=run(d,demand,c['k'],alg,c['seed'],'weighted',chr_env=env,binary=binary)
        assert r['qos']['integrity_errors']==0; return 1
    done=0; fails=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        fut={pool.submit(work,j):j for j in jobs}
        for f in concurrent.futures.as_completed(fut):
            try: done+=f.result()
            except Exception as exc: fails.append(dict(job=[fut[f][0]['name'],fut[f][1]],error=repr(exc))); print('FAILED',fut[f][0]['name'],fut[f][1],repr(exc),flush=True)
    (OUT/'progress.json').write_text(json.dumps(dict(expected=len(jobs),done=done,failures=fails),indent=2)+'\n')
    print(f'SAQR-SC PILOT: {done}/{len(jobs)} runs, {len(fails)} failures',flush=True)

if __name__=='__main__': main()
