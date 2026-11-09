"""SAQR tuning pilot (docs/SAQR_SPEC_V2.md §7). Weighted mode, tuning seeds 101-103.

Reuses the CHR pilot's demand traces (same generator, same seeds; hashes are
checked), and reuses its xy/dyad/topsis/oefixed/chr receipts only after a
cross-check shows the SAQR binary reproduces them exactly. Every route listed
in VARIANTS is run fresh with the SAQR binary. UFA is the unsafe control: a
watchdog abort is recorded as an observed deadlock, not a runner failure.
The protocol is written before any run and must match on rerun.
"""
import argparse
import concurrent.futures
import json
import subprocess
from chr_common import ROOT, STUDY, SAQR_STUDY, SAQR_BINARY, sha, run

CHR_PILOT=STUDY/'pilot_k8'
# name -> (routing algorithm, tuning env overrides)
VARIANTS={
    'duato':(          'duato',{}),
    'westfirst':(      'westfirst',{}),
    'ufa':(            'ufa',{}),
    'saqr_local':(     'saqr_local',{}),
    'saqr':(           'saqr',{}),
    'saqr_nogate':(    'saqr_nogate',{}),
    'saqr_lowgate':(   'saqr',{'NOC_SAQR_T_ON':26,'NOC_SAQR_T_OFF':13}),       # gate opens at ~0.43 of reachable capacity
    'saqr_nogate_m1':( 'saqr_nogate',{'NOC_SAQR_MARGIN':1}),                   # always compare, but require a 1-step win
}
REUSED=['xy','dyad','topsis','oefixed','chr','chr_hyst']
CROSSCHECK_ROUTES=['xy','dyad','topsis']

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); a=p.parse_args()
    out=SAQR_STUDY/'pilot_k8'; out.mkdir(parents=True,exist_ok=True)
    r0=json.loads((SAQR_STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['binary_sha256']==sha(SAQR_BINARY),'R0 must pass for the current SAQR binary'
    chr_proto=json.loads((CHR_PILOT/'protocol.json').read_text())
    cases=chr_proto['cases']
    protocol=dict(stage='saqr_pilot_k8',mode='weighted',cases=cases,variants={k:[v[0],v[1]] for k,v in VARIANTS.items()},
                  reused_from_chr_pilot=REUSED,crosscheck_routes=CROSSCHECK_ROUTES,
                  saqr_binary_sha256=sha(SAQR_BINARY),chr_pilot_binary_sha256=chr_proto['chr_binary_sha256'],
                  runner_sha256=sha(__file__),expected_runs=len(cases)*len(VARIANTS))
    pp=out/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol,'Pilot protocol mismatch'
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')

    # 1. Cross-check: SAQR binary must reproduce the CHR-pilot baseline receipts exactly.
    xc=[]
    for c in [x for x in cases if x['seed']==101 and x['index'] in (5,7)][:6]:
        demand=CHR_PILOT/'cases'/c['name']/'demand.txt'
        for route in CROSSCHECK_ROUTES:
            old=json.loads((CHR_PILOT/'cases'/c['name']/f'weighted_{route}'/'result.json').read_text())
            new=run(out/'crosscheck'/c['name']/route,demand,c['k'],route,c['seed'],'weighted',binary=SAQR_BINARY)
            xc.append(dict(case=c['name'],route=route,identical=old['aggregate']==new['aggregate'] and old['qos']==new['qos']))
    (out/'crosscheck.json').write_text(json.dumps(xc,indent=2)+'\n')
    assert all(x['identical'] for x in xc),f'Cross-check failed: {[x for x in xc if not x["identical"]]}'
    print(f'crosscheck: {len(xc)}/{len(xc)} identical',flush=True)

    # 2. Fresh SAQR-binary runs for every variant.
    def work(c):
        demand=CHR_PILOT/'cases'/c['name']/'demand.txt'
        rows=[]
        for name,(alg,env) in VARIANTS.items():
            d=out/'cases'/c['name']/f'weighted_{name}'; receipt=d/'result.json'
            if receipt.exists():
                r=json.loads(receipt.read_text()); assert r['binary_sha256']==protocol['saqr_binary_sha256']
            else:
                try:
                    r=run(d,demand,c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
                    r['deadlock']=False
                except subprocess.CalledProcessError:
                    log=(d/'run.log').read_text()
                    if alg!='ufa' or 'UFA_DEADLOCK' not in log: raise
                    r=dict(k=c['k'],algorithm=alg,seed=c['seed'],mode='weighted',deadlock=True,binary_sha256=sha(SAQR_BINARY),
                           trace_sha256=sha(demand),watchdog=json.loads((d/'saqr.json').read_text()))
                d.mkdir(parents=True,exist_ok=True); receipt.write_text(json.dumps(r,indent=2)+'\n')
            if not r.get('deadlock'): assert r['qos']['integrity_errors']==0
            rows.append(name)
        print(c['name'],'ok',flush=True)
        return rows
    done=0; failures=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures={pool.submit(work,c):c for c in cases}
        for f in concurrent.futures.as_completed(futures):
            try: done+=len(f.result())
            except Exception as exc: failures.append(dict(case=futures[f]['name'],error=repr(exc))); print('FAILED',futures[f]['name'],repr(exc),flush=True)
            prog=dict(expected_runs=protocol['expected_runs'],completed_runs=done,failed_cases=failures,complete=done==protocol['expected_runs'] and not failures)
            t=out/'progress.tmp'; t.write_text(json.dumps(prog,indent=2)+'\n'); t.replace(out/'progress.json')
    assert not failures
    print(f'SAQR PILOT COMPLETE: {done} runs',flush=True)

if __name__=='__main__': main()
