"""Summarize a CHR pilot stage: per-route means and seed-paired differences.

Metric definitions match scripts/prepare_qos_results.py. Paired intervals use
the t distribution over seeds (n=3 here); they are exploratory, pointwise and
not multiplicity-adjusted. Writes summary.csv, paired.csv and SUMMARY.md
into the stage folder.
"""
import argparse
import csv
import json
import math
from pathlib import Path
from chr_common import STUDY

T95={2:12.706,3:4.303,4:3.182,5:2.776}

def metrics(r):
    k=r['k']; q=r['qos']['classes']; crit,be=q[0],q[1]
    elig=crit['target_eligible_packets']
    h=r['chr']['classes']
    dual=sum(c['dual_candidate_decisions'] for c in h)
    return dict(critical_p99=crit['latency_p99_cycles'],best_effort_p99=be['latency_p99_cycles'],
                throughput=sum(c['ejected_flits'] for c in q)/(r['cycles']*k*k),
                critical_miss_pct=100*crit['target_missed_packets']/elig if elig else math.nan,
                pending_growth=sum(c['pending_end']-c['pending_start'] for c in q),
                best_effort_pending_end=be['pending_end'],
                switched_pct=100*sum(c['switched_decisions'] for c in h)/dual if dual else 0.0)

def mean_ci(v):
    n=len(v); m=sum(v)/n
    if n<2: return m,math.nan
    s=math.sqrt(sum((x-m)**2 for x in v)/(n-1)); return m,T95.get(n,1.96)*s/math.sqrt(n)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',default='pilot_k8'); a=p.parse_args()
    out=STUDY/a.stage; proto=json.loads((out/'protocol.json').read_text())
    data={}
    for c in proto['cases']:
        for route in proto['routes']:
            r=json.loads((out/'cases'/c['name']/f'weighted_{route}'/'result.json').read_text())
            data[(c['traffic'],c['load'],c['seed'],route)]=metrics(r)
    keys=sorted({(t,l) for t,l,_,_ in data})
    seeds=sorted({s for _,_,s,_ in data}); names=list(next(iter(data.values())))
    rows=[]
    for t,l in keys:
        for route in proto['routes']:
            row=dict(traffic=t,load=l,route=route)
            for m in names:
                mu,ci=mean_ci([data[(t,l,s,route)][m] for s in seeds]); row[m]=mu; row[m+'_ci']=ci
            rows.append(row)
    with (out/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    paired=[]
    for t,l in keys:
        for route in proto['routes']:
            for ref in ('xy','dyad','topsis','oefixed'):
                if route==ref: continue
                for m in ('critical_p99','best_effort_p99','throughput','critical_miss_pct'):
                    xs=[data[(t,l,s,route)][m] for s in seeds]; ys=[data[(t,l,s,ref)][m] for s in seeds]
                    mu,ci=mean_ci([x-y for x,y in zip(xs,ys)])
                    refm=sum(ys)/len(ys)
                    paired.append(dict(traffic=t,load=l,route=route,ref=ref,metric=m,diff=mu,ci95=ci,
                                       rel_pct=100*mu/refm if refm else math.nan,
                                       rel_lo_pct=100*(mu-ci)/refm if refm else math.nan,
                                       rel_hi_pct=100*(mu+ci)/refm if refm else math.nan))
    with (out/'paired.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired[0])); w.writeheader(); w.writerows(paired)
    # Markdown digest: one table per traffic.
    lines=[f'# {a.stage}: exploratory pilot summary','',
           'Weighted mode, seeds '+', '.join(map(str,seeds))+'. Means over seeds. Exploratory tuning evidence, not held-out.',
           'Throughput = total ejected flits/node/cycle. Misses = critical target misses (%). Sw = % of two-candidate decisions that left the default port.','']
    for t in sorted({t for t,_ in keys}):
        lines+=[f'## {t}','','| load | route | crit p99 | BE p99 | throughput | crit miss % | pending growth | sw % |','|---:|---|---:|---:|---:|---:|---:|---:|']
        for r in rows:
            if r['traffic']!=t: continue
            lines.append(f"| {r['load']:.4g} | {r['route']} | {r['critical_p99']:.1f} | {r['best_effort_p99']:.1f} | {r['throughput']:.5f} | "
                         f"{r['critical_miss_pct']:.2f} | {r['pending_growth']:.0f} | {r['switched_pct']:.1f} |")
        lines.append('')
    (out/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
