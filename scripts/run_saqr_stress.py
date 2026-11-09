"""Drain stress test (docs/SAQR_SPEC_V2.md §6.4): after the overload window,
BookSim keeps stepping until every generated packet (including source
backlog) is delivered. A deadlock-free route must finish; a hang hits the
timeout. Uses frozen highest-load traces for plumbing only."""
import concurrent.futures, json, os, subprocess, time
from chr_common import ROOT, SAQR_STUDY, SAQR_BINARY, sha, config
ROUTES=['saqr','saqr_local','saqr_nogate','duato','westfirst','xy']
CASES=[('k8_uniform_l8_s1',8),('k8_transpose_l8_s1',8),('k8_hotspot_center_l8_s1',8),('k4_transpose_l8_s1',4)]
def work(name,k,alg):
    d=SAQR_STUDY/'stress'/name/alg; d.mkdir(parents=True,exist_ok=True)
    cfg=d/'config.cfg'; cfg.write_text(config(k,alg,1,'weighted'))
    env={x:y for x,y in os.environ.items() if not x.startswith('NOC_')}
    env.update(NOC_TRACE=str(ROOT/'results/qos_comparison/cases'/name/'demand.txt'),NOC_WARMUP='5000',NOC_MEASURE='20000',
               NOC_QOS_MODE='weighted',NOC_METRICS=str(d/'aggregate.json'),NOC_QOS_METRICS=str(d/'classes.json'))
    t=time.perf_counter()
    try:
        with (d/'run.log').open('w') as out:
            subprocess.run([str(SAQR_BINARY),str(cfg)],stdout=out,stderr=subprocess.STDOUT,env=env,timeout=1800,check=True)
        log=(d/'run.log').read_text()
        done='Time taken is' in log
        taken=[l for l in log.splitlines() if 'Time taken is' in l]
        return dict(case=name,route=alg,drained=done,end=taken[-1] if taken else None,wall=round(time.perf_counter()-t,1))
    except subprocess.TimeoutExpired:
        return dict(case=name,route=alg,drained=False,end='TIMEOUT',wall=round(time.perf_counter()-t,1))
    except subprocess.CalledProcessError as e:
        return dict(case=name,route=alg,drained=False,end=f'exit {e.returncode}: '+(d/'run.log').read_text()[-200:],wall=round(time.perf_counter()-t,1))
jobs=[(n,k,a) for n,k in CASES for a in ROUTES]
with concurrent.futures.ThreadPoolExecutor(8) as pool:
    res=list(pool.map(lambda j: work(*j),jobs))
for r in res: print(r,flush=True)
receipt=dict(binary_sha256=sha(SAQR_BINARY),runs=len(res),drained=sum(r['drained'] for r in res),results=res,
             status='pass' if all(r['drained'] for r in res) else 'fail')
(SAQR_STUDY/'stress'/'stress_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('STRESS',receipt['status'],f"{receipt['drained']}/{receipt['runs']} drained")
