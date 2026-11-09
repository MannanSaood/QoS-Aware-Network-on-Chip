"""SAQR 16x16 two-tier stage (docs/SAQR_SPEC_V2.md §14). Weighted mode, tuning seeds 101-103.

Runs the two-tier variant(s) chosen after 8x8 round 4 on the §13 16x16
traces. The rebuilt binary must first reproduce §13 receipts exactly for
xy, duato, saqr_nogate and saqr_nogate_crit (cross-check) so that the §13
routes can be compared directly. The variant choice is recorded in the
protocol before any run.
"""
import argparse
import concurrent.futures
import json
from chr_common import SAQR_STUDY, SAQR_BINARY, sha, run
from run_saqr_pilot4 import VARIANTS as R4

STAGE=SAQR_STUDY/'stage_k16'
CROSSCHECK={'xy':('xy',{}),'duato':('duato',{}),'saqr_nogate':('saqr_nogate',{}),'saqr_nogate_crit':('saqr_nogate',{'NOC_SAQR_CLASS_MASK':1})}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); p.add_argument('--variants',nargs='+',required=True); a=p.parse_args()
    variants={v:R4[v] for v in a.variants}
    out=SAQR_STUDY/'stage_k16_twotier'; out.mkdir(parents=True,exist_ok=True)
    r0=json.loads((SAQR_STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['binary_sha256']==sha(SAQR_BINARY),'R0 must pass for the current SAQR binary'
    r4=json.loads((SAQR_STUDY/'pilot_k8_r4/progress.json').read_text()); assert r4['complete'],'Round 4 must be complete first'
    cases=json.loads((STAGE/'protocol.json').read_text())['cases']
    protocol=dict(stage='saqr_stage_k16_twotier',mode='weighted',cases=cases,variants={k:[v[0],v[1]] for k,v in variants.items()},
                  chosen_after='pilot_k8_r4',saqr_binary_sha256=sha(SAQR_BINARY),runner_sha256=sha(__file__),
                  expected_runs=len(cases)*len(variants))
    pp=out/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol,'Stage protocol mismatch'
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')

    jobs=[(c,r) for c in cases if c['seed']==101 and c['index'] in (6,8) and c['traffic']!='hotspot_center' for r in CROSSCHECK]
    def xc(job):
        c,route=job; alg,env=CROSSCHECK[route]
        old=json.loads((STAGE/'cases'/c['name']/f'weighted_{route}'/'result.json').read_text())
        new=run(out/'crosscheck'/c['name']/route,STAGE/'cases'/c['name']/'demand.txt',c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
        return dict(case=c['name'],route=route,identical=old['aggregate']==new['aggregate'] and old['qos']==new['qos'])
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool: res=list(pool.map(xc,jobs))
    (out/'crosscheck.json').write_text(json.dumps(res,indent=2)+'\n')
    assert all(x['identical'] for x in res),f'Cross-check failed: {[x for x in res if not x["identical"]]}'
    print(f'crosscheck: {len(res)}/{len(res)} identical to §13 receipts',flush=True)

    def work(c):
        demand=STAGE/'cases'/c['name']/'demand.txt'
        for name,(alg,env) in variants.items():
            d=out/'cases'/c['name']/f'weighted_{name}'; receipt=d/'result.json'
            if receipt.exists():
                r=json.loads(receipt.read_text()); assert r['binary_sha256']==protocol['saqr_binary_sha256']
            else: r=run(d,demand,c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
            assert r['qos']['integrity_errors']==0
        print(c['name'],'ok',flush=True)
        return len(variants)
    done=0; failures=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures={pool.submit(work,c):c for c in cases}
        for f in concurrent.futures.as_completed(futures):
            try: done+=f.result()
            except Exception as exc: failures.append(dict(case=futures[f]['name'],error=repr(exc))); print('FAILED',futures[f]['name'],repr(exc),flush=True)
            prog=dict(expected_runs=protocol['expected_runs'],completed_runs=done,failed_cases=failures,complete=done==protocol['expected_runs'] and not failures)
            t=out/'progress.tmp'; t.write_text(json.dumps(prog,indent=2)+'\n'); t.replace(out/'progress.json')
    assert not failures
    print(f'SAQR 16x16 TWO-TIER: {done} runs',flush=True)

if __name__=='__main__': main()
