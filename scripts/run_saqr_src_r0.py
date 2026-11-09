"""Gates for the SAQR-SC binary (§19), before any SAQR-SC run.

R0: the 144 frozen showcase receipts (xy/dyad/topsis, k = 4 and 8, both modes)
must be reproduced exactly (same cases as scripts/run_chr_r0.py, reused unchanged).
X1: with the classifier disabled, the SAQR-SC binary must reproduce the round-7
SAQR receipts exactly (saqr_o1t_both, saqr_nogate_crit, duato; 8x8 seeds 101-103).
"""
import argparse
import concurrent.futures
import json
import run_chr_r0 as r0
from chr_common import STUDY
from saqr_src_common import SAQR_STUDY, SRC_BINARY, SRC_STUDY, sha, run

R7=SAQR_STUDY/'pilot_k8_r7'; R3=SAQR_STUDY/'pilot_k8_r3'; R1=SAQR_STUDY/'pilot_k8'
X1={'saqr_o1t_both':('saqr_nogate',{'NOC_SAQR_O1TURN_MASK':3},R7),
    'saqr_nogate_crit':('saqr_nogate',{'NOC_SAQR_CLASS_MASK':1},R3),
    'duato':('duato',{},R1)}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); a=p.parse_args()
    r0.OUT=SRC_STUDY/'r0'; r0.BINARY=SRC_BINARY; r0.OUT.mkdir(parents=True,exist_ok=True)
    rows=[]; fails=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        for c,f in [(c,pool.submit(r0.work,c)) for c in r0.cases()]:
            try: rows.append(f.result())
            except Exception as exc: fails.append(dict(case=c,error=repr(exc)))
    cases=json.loads((SAQR_STUDY/'pilot_k8/protocol.json').read_text())['cases']
    def x1(job):
        c,name=job; alg,env,ref=X1[name]
        d=SRC_STUDY/'x1'/c['name']/name
        new=run(d,STUDY/'pilot_k8'/'cases'/c['name']/'demand.txt',c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SRC_BINARY)
        old=json.loads((ref/'cases'/c['name']/f'weighted_{name}'/'result.json').read_text())
        return dict(case=c['name'],route=name,identical=old['aggregate']==new['aggregate'] and old['qos']==new['qos'] and old['trace_sha256']==new['trace_sha256'])
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        xs=list(pool.map(x1,[(c,n) for c in cases for n in X1]))
    receipt=dict(gate='R0+X1',build='saqr_src',binary_sha256=sha(SRC_BINARY),
                 r0_runs=len(rows),r0_identical=sum(r['identical'] for r in rows),r0_failures=fails,
                 x1_runs=len(xs),x1_identical=sum(x['identical'] for x in xs),x1_differing=[x for x in xs if not x['identical']])
    receipt['status']='pass' if receipt['r0_runs']==144 and receipt['r0_identical']==144 and not fails and receipt['x1_identical']==len(xs) else 'fail'
    (SRC_STUDY/'r0').mkdir(parents=True,exist_ok=True)
    (SRC_STUDY/'r0'/'r0_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('x1_differing',)},indent=2))

if __name__=='__main__': main()
