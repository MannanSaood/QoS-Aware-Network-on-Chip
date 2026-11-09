"""R0 regression gate (docs/CHR_OE_CANDIDATE_SPEC.md section 4).

The CHR build must reproduce the frozen showcase metrics exactly for XY,
DyAD-OE and TOPSIS-OE in both scheduling modes. It replays the frozen
demand traces (read-only, hash-checked) and writes only under
results/chr_study/r0.
"""
import argparse
import concurrent.futures
import json
from chr_common import ROOT, STUDY, SAQR_STUDY, CHR_BINARY, SAQR_BINARY, sha, run

FROZEN=ROOT/'results/qos_comparison/cases'
OUT=STUDY/'r0'
BINARY=CHR_BINARY
TRAFFIC=['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center']

def cases():
    for k in (4,8):
        for traffic in TRAFFIC:
            for index in (3,7):
                for mode in ('age','weighted'):
                    for algorithm in ('xy','dyad','topsis'):
                        yield dict(k=k,name=f'k{k}_{traffic}_l{index}_s1',mode=mode,algorithm=algorithm)

def work(c):
    frozen_dir=FROZEN/c['name']/f"{c['mode']}_{c['algorithm']}"
    frozen=json.loads((frozen_dir/'result.json').read_text())
    demand=FROZEN/c['name']/'demand.txt'
    assert sha(demand)==frozen['trace_sha256'],'Frozen trace hash mismatch'
    new=run(OUT/c['name']/f"{c['mode']}_{c['algorithm']}",demand,c['k'],c['algorithm'],frozen['seed'],c['mode'],binary=BINARY)
    assert new['config_sha256']==frozen['config_sha256'],'Config differs from frozen run'
    same_aggregate=new['aggregate']==frozen['aggregate']
    same_qos=new['qos']==frozen['qos']
    return dict(case=c,identical=same_aggregate and same_qos,aggregate_identical=same_aggregate,qos_identical=same_qos,
                frozen_wall=frozen['wall_seconds'],chr_wall=new['wall_seconds'])

def main():
    global OUT,BINARY
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=8); p.add_argument('--build',choices=['chr','saqr'],default='chr'); a=p.parse_args()
    if a.build=='saqr': OUT,BINARY=SAQR_STUDY/'r0',SAQR_BINARY
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]; failures=[]
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures={pool.submit(work,c):c for c in cases()}
        for f in concurrent.futures.as_completed(futures):
            c=futures[f]
            try:
                r=f.result(); rows.append(r)
                print(c['name'],c['mode'],c['algorithm'],'IDENTICAL' if r['identical'] else 'DIFFERS',flush=True)
            except Exception as exc:
                failures.append(dict(case=c,error=repr(exc))); print('FAILED',c,repr(exc),flush=True)
    receipt=dict(gate='R0',build=a.build,binary_sha256=sha(BINARY),chr_binary_sha256=sha(CHR_BINARY),frozen_binary_sha256='bb3f1024a6308c2ed1e99d429a20b0ef373d06c8fdda29a26cf62fe02a178a24',
                 runs=len(rows),identical=sum(r['identical'] for r in rows),failures=failures,
                 status='pass' if rows and not failures and all(r['identical'] for r in rows) else 'fail',
                 differing=[r['case'] for r in rows if not r['identical']],
                 wall_ratio_chr_over_frozen=sum(r['chr_wall'] for r in rows)/max(1e-9,sum(r['frozen_wall'] for r in rows)))
    (OUT/'r0_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='differing'},indent=2))

if __name__=='__main__': main()
