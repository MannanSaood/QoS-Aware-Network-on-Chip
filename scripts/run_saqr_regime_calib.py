"""Regime-detector calibration (§16). Observe mode only: the detector is
computed and logged but never gates routing, so each run must reproduce its
earlier receipt exactly. 8x8 tuning traces (seeds 101-103), two routings:
  obs_crit   = saqr_nogate_crit (best effort pure XY): the signal BE would see before adapting
  obs_nogate = saqr_nogate (best effort adapting): whether the signal persists once BE adapts
Thresholds are chosen from these runs (tuning data) and recorded in §16 before round 6."""
import argparse
import concurrent.futures
import json
from chr_common import STUDY, SAQR_STUDY, SAQR_BINARY, sha, run

CHR_PILOT=STUDY/'pilot_k8'
OBS={'NOC_SAQR_REGIME_OBSERVE':1}
VARIANTS={'obs_crit':('saqr_nogate',{'NOC_SAQR_CLASS_MASK':1,**OBS},SAQR_STUDY/'pilot_k8_r3','saqr_nogate_crit'),
          'obs_nogate':('saqr_nogate',dict(OBS),SAQR_STUDY/'pilot_k8','saqr_nogate')}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); a=p.parse_args()
    out=SAQR_STUDY/'regime_calib'; out.mkdir(parents=True,exist_ok=True)
    r0=json.loads((SAQR_STUDY/'r0/r0_receipt.json').read_text())
    assert r0['status']=='pass' and r0['binary_sha256']==sha(SAQR_BINARY),'R0 must pass for the current SAQR binary'
    cases=json.loads((CHR_PILOT/'protocol.json').read_text())['cases']
    protocol=dict(stage='saqr_regime_calibration',cases=cases,variants={k:[v[0],v[1]] for k,v in VARIANTS.items()},
                  saqr_binary_sha256=sha(SAQR_BINARY),runner_sha256=sha(__file__))
    pp=out/'protocol.json'
    if pp.exists(): assert json.loads(pp.read_text())==protocol
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')
    def work(c):
        rows=[]
        for name,(alg,env,ref,refname) in VARIANTS.items():
            d=out/'cases'/c['name']/name
            r=json.loads((d/'result.json').read_text()) if (d/'result.json').exists() else \
              run(d,CHR_PILOT/'cases'/c['name']/'demand.txt',c['k'],alg,c['seed'],'weighted',chr_env=env,binary=SAQR_BINARY)
            old=json.loads((ref/'cases'/c['name']/f'weighted_{refname}'/'result.json').read_text())
            assert old['aggregate']==r['aggregate'] and old['qos']==r['qos'],f'observe mode changed results: {c["name"]} {name}'
            g=r['saqr']['regime']; h=g['ratio_hist_tenths']; n=sum(h)
            def pct(q):
                acc=0
                for b,v in enumerate(h):
                    acc+=v
                    if acc>=q*n: return b/10
                return 19.9
            rows.append(dict(case=c['name'],traffic=c['traffic'],index=c['index'],seed=c['seed'],variant=name,
                             mean_x=g['sum_x']/g['samples']/256,mean_y=g['sum_y']/g['samples']/256,
                             ratio_of_means=g['sum_x']/max(1,g['sum_y']),p05=pct(.05),p25=pct(.25),p50=pct(.5),p75=pct(.75),p95=pct(.95)))
        print(c['name'],'ok',flush=True); return rows
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        for rr in pool.map(work,cases): rows+=rr
    (out/'calibration.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('CALIBRATION COMPLETE',len(rows),flush=True)

if __name__=='__main__': main()
