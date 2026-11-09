"""SAQR tuning pilot, round 4: two-tier (per-class) adaptivity. Weighted mode, tuning seeds 101-103.

Critical traffic (class 0) always compares ports with the additive rule
(the saqr_nogate rule that won transpose critical p99). Best effort (class 1)
adapts only under strong asymmetry (ratio test), optionally also behind the
hysteresis gate. Same 8x8 traces as rounds 1-3. Earlier receipts are reused
only after the rebuilt binary reproduces them exactly (cross-check).
"""
import argparse
import concurrent.futures
import json
from chr_common import STUDY, SAQR_STUDY, SAQR_BINARY, sha, run

CHR_PILOT=STUDY/'pilot_k8'
ROUND1=SAQR_STUDY/'pilot_k8'
ROUND3=SAQR_STUDY/'pilot_k8_r3'
VARIANTS={
    'twotier_g_r2':(  'saqr_nogate',{'NOC_SAQR_BE_GATE':1,'NOC_SAQR_BE_RATIO_NUM':2,'NOC_SAQR_BE_RATIO_DEN':1}),
    'twotier_g_r3':(  'saqr_nogate',{'NOC_SAQR_BE_GATE':1,'NOC_SAQR_BE_RATIO_NUM':3,'NOC_SAQR_BE_RATIO_DEN':1}),
    'twotier_r2':(    'saqr_nogate',{'NOC_SAQR_BE_RATIO_NUM':2,'NOC_SAQR_BE_RATIO_DEN':1}),
}
CROSSCHECK_CHR=['xy','dyad','topsis']
CROSSCHECK_SAQR={'saqr':(ROUND1,'saqr',{}),'saqr_nogate':(ROUND1,'saqr_nogate',{}),'duato':(ROUND1,'duato',{}),
                 'saqr_nogate_crit':(ROUND3,'saqr_nogate',{'NOC_SAQR_CLASS_MASK':1})}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); a=p.parse_args()
    out=SAQR_STUDY/'pilot_k8_r4'; out.mkdir(parents=True,exist_ok=True)
    r0=json.loads((SAQR_STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['binary_sha256']==sha(SAQR_BINARY),'R0 must pass for the current SAQR binary'
    cases=json.loads((CHR_PILOT/'protocol.json').read_text())['cases']
    protocol=dict(stage='saqr_pilot_k8_round4',mode='weighted',cases=cases,variants={k:[v[0],v[1]] for k,v in VARIANTS.items()},
                  saqr_binary_sha256=sha(SAQR_BINARY),runner_sha256=sha(__file__),expected_runs=len(cases)*len(VARIANTS))
    pp=out/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol,'Pilot protocol mismatch'
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')

    xc_jobs=[]
    for c in [x for x in cases if x['seed']==101 and x['index'] in (5,7)][:6]:
        for route in CROSSCHECK_CHR: xc_jobs.append((c,route,CHR_PILOT,route,{}))
        for route,(base,alg,env) in CROSSCHECK_SAQR.items(): xc_jobs.append((c,route,base,alg,env))
    def xc(job):
        c,route,base,alg,env=job
        old=json.loads((base/'cases'/c['name']/f'weighted_{route}'/'result.json').read_text())
        new=run(out/'crosscheck'/c['name']/route,CHR_PILOT/'cases'/c['name']/'demand.txt',c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
        return dict(case=c['name'],route=route,identical=old['aggregate']==new['aggregate'] and old['qos']==new['qos'])
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool: res=list(pool.map(xc,xc_jobs))
    (out/'crosscheck.json').write_text(json.dumps(res,indent=2)+'\n')
    assert all(x['identical'] for x in res),f'Cross-check failed: {[x for x in res if not x["identical"]]}'
    print(f'crosscheck: {len(res)}/{len(res)} identical',flush=True)

    def work(c):
        demand=CHR_PILOT/'cases'/c['name']/'demand.txt'
        for name,(alg,env) in VARIANTS.items():
            d=out/'cases'/c['name']/f'weighted_{name}'; receipt=d/'result.json'
            if receipt.exists():
                r=json.loads(receipt.read_text()); assert r['binary_sha256']==protocol['saqr_binary_sha256']
            else: r=run(d,demand,c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
            assert r['qos']['integrity_errors']==0
        print(c['name'],'ok',flush=True)
        return len(VARIANTS)
    done=0; failures=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures={pool.submit(work,c):c for c in cases}
        for f in concurrent.futures.as_completed(futures):
            try: done+=f.result()
            except Exception as exc: failures.append(dict(case=futures[f]['name'],error=repr(exc))); print('FAILED',futures[f]['name'],repr(exc),flush=True)
            prog=dict(expected_runs=protocol['expected_runs'],completed_runs=done,failed_cases=failures,complete=done==protocol['expected_runs'] and not failures)
            t=out/'progress.tmp'; t.write_text(json.dumps(prog,indent=2)+'\n'); t.replace(out/'progress.json')
    assert not failures
    print(f'SAQR PILOT ROUND 4 COMPLETE: {done} runs',flush=True)

if __name__=='__main__': main()
