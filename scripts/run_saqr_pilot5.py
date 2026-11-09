"""SAQR tuning pilot, round 5: hop-delay diagnostic and stall-triggered best effort (§15).
Weighted mode, tuning seeds 101-103, the same 8x8 traces as rounds 1-4.

DIAG variants rerun earlier routes on the new binary. Their aggregate and QoS
metrics must equal the earlier receipts exactly (the diagnostic is read-only);
the reruns add per-hop delay counters. `saqr_xyref` routes every packet XY
through the SAQR code path (class mask 0) to give an XY hop-delay reference;
its equality with the frozen XY route is recorded, not assumed.
STALL variants: critical as saqr_nogate, best effort XY until its head flit has
failed VC allocation for W cycles at a router, then XY-preferred with the
other productive port as fallback.
"""
import argparse
import concurrent.futures
import json
from chr_common import STUDY, SAQR_STUDY, SAQR_BINARY, sha, run

CHR_PILOT=STUDY/'pilot_k8'
R1,R3,R4=SAQR_STUDY/'pilot_k8',SAQR_STUDY/'pilot_k8_r3',SAQR_STUDY/'pilot_k8_r4'
DIAG={  # name -> (algorithm, env, earlier receipt dir or None)
    'saqr_nogate':(      'saqr_nogate',{},R1),
    'saqr_nogate_crit':( 'saqr_nogate',{'NOC_SAQR_CLASS_MASK':1},R3),
    'twotier_g_r3':(     'saqr_nogate',{'NOC_SAQR_BE_GATE':1,'NOC_SAQR_BE_RATIO_NUM':3,'NOC_SAQR_BE_RATIO_DEN':1},R4),
    'saqr_xyref':(       'saqr_nogate',{'NOC_SAQR_CLASS_MASK':0},None),
}
STALL={f'stall_w{w}':('saqr_nogate',{'NOC_SAQR_BE_STALL':w}) for w in (8,32,128)}
VARIANTS={**{k:(v[0],v[1]) for k,v in DIAG.items()},**STALL}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); a=p.parse_args()
    out=SAQR_STUDY/'pilot_k8_r5'; out.mkdir(parents=True,exist_ok=True)
    r0=json.loads((SAQR_STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['binary_sha256']==sha(SAQR_BINARY),'R0 must pass for the current SAQR binary'
    cases=json.loads((CHR_PILOT/'protocol.json').read_text())['cases']
    protocol=dict(stage='saqr_pilot_k8_round5',mode='weighted',cases=cases,variants={k:[v[0],v[1]] for k,v in VARIANTS.items()},
                  diag_reference={k:(str(v[2].name) if v[2] else None) for k,v in DIAG.items()},
                  saqr_binary_sha256=sha(SAQR_BINARY),runner_sha256=sha(__file__),expected_runs=len(cases)*len(VARIANTS))
    pp=out/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol,'Pilot protocol mismatch'
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')

    # Baseline cross-check against the CHR-pilot receipts (xy/dyad/topsis).
    jobs=[(c,r) for c in [x for x in cases if x['seed']==101 and x['index'] in (5,7)][:6] for r in ('xy','dyad','topsis')]
    def xc(job):
        c,route=job
        old=json.loads((CHR_PILOT/'cases'/c['name']/f'weighted_{route}'/'result.json').read_text())
        new=run(out/'crosscheck'/c['name']/route,CHR_PILOT/'cases'/c['name']/'demand.txt',c['k'],route,c['seed'],'weighted',binary=SAQR_BINARY)
        return dict(case=c['name'],route=route,identical=old['aggregate']==new['aggregate'] and old['qos']==new['qos'])
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool: res=list(pool.map(xc,jobs))
    (out/'crosscheck.json').write_text(json.dumps(res,indent=2)+'\n')
    assert all(x['identical'] for x in res),f'Cross-check failed: {[x for x in res if not x["identical"]]}'
    print(f'crosscheck: {len(res)}/{len(res)} identical',flush=True)

    def work(c):
        demand=CHR_PILOT/'cases'/c['name']/'demand.txt'; rows=[]
        for name,(alg,env) in VARIANTS.items():
            d=out/'cases'/c['name']/f'weighted_{name}'; receipt=d/'result.json'
            if receipt.exists():
                r=json.loads(receipt.read_text()); assert r['binary_sha256']==protocol['saqr_binary_sha256']
            else: r=run(d,demand,c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
            assert r['qos']['integrity_errors']==0
            ref = DIAG[name][2] if name in DIAG else None
            if ref is not None:
                old=json.loads((ref/'cases'/c['name']/f'weighted_{name}'/'result.json').read_text())
                assert old['aggregate']==r['aggregate'] and old['qos']==r['qos'],f'Diagnostic rerun differs: {c["name"]} {name}'
            if name=='saqr_xyref':
                old=json.loads((CHR_PILOT/'cases'/c['name']/'weighted_xy'/'result.json').read_text())
                rows.append(dict(case=c['name'],xyref_identical_to_xy=old['aggregate']==r['aggregate'] and old['qos']==r['qos']))
        print(c['name'],'ok',flush=True)
        return rows
    done=0; failures=[]; xyref=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures={pool.submit(work,c):c for c in cases}
        for f in concurrent.futures.as_completed(futures):
            try: xyref+=f.result(); done+=len(VARIANTS)
            except Exception as exc: failures.append(dict(case=futures[f]['name'],error=repr(exc))); print('FAILED',futures[f]['name'],repr(exc),flush=True)
            prog=dict(expected_runs=protocol['expected_runs'],completed_runs=done,failed_cases=failures,complete=done==protocol['expected_runs'] and not failures)
            t=out/'progress.tmp'; t.write_text(json.dumps(prog,indent=2)+'\n'); t.replace(out/'progress.json')
    (out/'xyref.json').write_text(json.dumps(sorted(xyref,key=lambda x:x['case']),indent=2)+'\n')
    print(f"xyref identical to frozen-path XY: {sum(x['xyref_identical_to_xy'] for x in xyref)}/{len(xyref)}",flush=True)
    assert not failures
    print(f'SAQR PILOT ROUND 5 COMPLETE: {done} runs',flush=True)

if __name__=='__main__': main()
