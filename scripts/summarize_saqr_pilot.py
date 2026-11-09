"""Summarize the SAQR 8x8 pilot together with the reused CHR-pilot baselines.

Metric definitions match scripts/prepare_qos_results.py. Paired t-intervals
over seeds are exploratory, pointwise and not multiplicity-adjusted. UFA runs
aborted by the deadlock watchdog are counted, not averaged.
"""
import csv
import json
import math
from chr_common import STUDY, SAQR_STUDY

T95={2:12.706,3:4.303,4:3.182,5:2.776}
CHR=STUDY/'pilot_k8'; OUT=SAQR_STUDY/'pilot_k8'; OUT2=SAQR_STUDY/'pilot_k8_r2'

def metrics(r):
    k=r['k']; q=r['qos']['classes']; crit,be=q[0],q[1]; elig=crit['target_eligible_packets']
    sw=math.nan
    if r.get('saqr') and r['saqr'].get('classes'):
        c=r['saqr']['classes']; routed=sum(x['routed'] for x in c); sw=100*sum(x['switched'] for x in c)/routed if routed else 0
    return dict(critical_p99=crit['latency_p99_cycles'],best_effort_p99=be['latency_p99_cycles'],
                throughput=sum(c['ejected_flits'] for c in q)/(r['cycles']*k*k),
                critical_miss_pct=100*crit['target_missed_packets']/elig if elig else math.nan,
                be_delivered_frac=be['delivered_packets']/max(1,be['generated_packets']+be['pending_start']),
                pending_growth=sum(c['pending_end']-c['pending_start'] for c in q),switched_pct=sw)

def mean_ci(v):
    v=[x for x in v if not math.isnan(x)]; n=len(v)
    if n==0: return math.nan,math.nan
    m=sum(v)/n
    if n<2: return m,math.nan
    s=math.sqrt(sum((x-m)**2 for x in v)/(n-1)); return m,T95.get(n,1.96)*s/math.sqrt(n)

def main():
    global OUT
    import sys
    proto=json.loads((OUT/'protocol.json').read_text())
    routes=proto['reused_from_chr_pilot']+list(proto['variants'])
    source={r:(CHR if r in proto['reused_from_chr_pilot'] else OUT) for r in routes}
    if '--round2' in sys.argv:
        p2=json.loads((OUT2/'protocol.json').read_text())
        for r in p2['variants']: routes.append(r); source[r]=OUT2
        OUT=OUT2
    if '--round3' in sys.argv:
        OUT3=SAQR_STUDY/'pilot_k8_r3'; p3=json.loads((OUT3/'protocol.json').read_text())
        for r in p3['variants']: routes.append(r); source[r]=OUT3
        OUT=OUT3
    if '--round4' in sys.argv:
        OUT4=SAQR_STUDY/'pilot_k8_r4'; p4=json.loads((OUT4/'protocol.json').read_text())
        for r in p4['variants']: routes.append(r); source[r]=OUT4
        OUT=OUT4
    if '--round5' in sys.argv:
        OUT5=SAQR_STUDY/'pilot_k8_r5'; p5=json.loads((OUT5/'protocol.json').read_text())
        for r in p5['variants']:
            if r not in source: routes.append(r)
            source[r]=OUT5
        OUT=OUT5
    if '--round6' in sys.argv:
        OUT6=SAQR_STUDY/'pilot_k8_r6'; p6=json.loads((OUT6/'protocol.json').read_text())
        for r in p6['variants']:
            if r not in source: routes.append(r)
            source[r]=OUT6
        OUT=OUT6
    if '--round7' in sys.argv:
        OUT7=SAQR_STUDY/'pilot_k8_r7'; p7=json.loads((OUT7/'protocol.json').read_text())
        for r in p7['variants']:
            if r not in source: routes.append(r)
            source[r]=OUT7
        OUT=OUT7
    data={}; deadlocks={}
    for c in proto['cases']:
        for route in routes:
            base=source[route]
            r=json.loads((base/'cases'/c['name']/f'weighted_{route}'/'result.json').read_text())
            key=(c['traffic'],c['load'],c['seed'],route)
            if r.get('deadlock'): deadlocks[key]=True; continue
            data[key]=metrics(r)
    keys=sorted({(t,l) for t,l,_,_ in [*data,*deadlocks]}); seeds=sorted({s for _,_,s,_ in data})
    names=['critical_p99','best_effort_p99','throughput','critical_miss_pct','be_delivered_frac','pending_growth','switched_pct']
    rows=[]
    for t,l in keys:
        for route in routes:
            row=dict(traffic=t,load=l,route=route,deadlocked_seeds=sum(1 for s in seeds if (t,l,s,route) in deadlocks))
            for m in names:
                mu,ci=mean_ci([data[(t,l,s,route)][m] for s in seeds if (t,l,s,route) in data]); row[m]=mu; row[m+'_ci']=ci
            rows.append(row)
    with (OUT/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    paired=[]
    for t,l in keys:
        for route in routes:
            for ref in ('xy','dyad','topsis','duato'):
                if route==ref: continue
                for m in ('critical_p99','best_effort_p99','throughput','critical_miss_pct'):
                    pairs=[(data[(t,l,s,route)][m],data[(t,l,s,ref)][m]) for s in seeds if (t,l,s,route) in data and (t,l,s,ref) in data]
                    if len(pairs)<2: continue
                    mu,ci=mean_ci([x-y for x,y in pairs]); refm=sum(y for _,y in pairs)/len(pairs)
                    paired.append(dict(traffic=t,load=l,route=route,ref=ref,metric=m,n=len(pairs),diff=mu,ci95=ci,
                        rel_pct=100*mu/refm if refm else math.nan,rel_lo_pct=100*(mu-ci)/refm if refm else math.nan,
                        rel_hi_pct=100*(mu+ci)/refm if refm else math.nan))
    with (OUT/'paired.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired[0])); w.writeheader(); w.writerows(paired)
    lines=['# SAQR 8x8 pilot: exploratory summary','',
           'Weighted mode, tuning seeds 101-103 (not held out). Means over seeds. xy/dyad/topsis/oefixed/chr/chr_hyst reused from the CHR pilot after an exact cross-check.',
           'Throughput = total ejected flits/node/cycle. Miss = critical target misses (%). BE frac = best-effort delivered fraction. DL = seeds deadlocked (UFA watchdog).','']
    for t in sorted({t for t,_ in keys}):
        lines+=[f'## {t}','','| load | route | crit p99 | BE p99 | throughput | crit miss % | BE frac | sw % | DL |','|---:|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in rows:
            if r['traffic']!=t: continue
            f=lambda v,fmt: '—' if isinstance(v,float) and math.isnan(v) else format(v,fmt)
            lines.append(f"| {r['load']:.4g} | {r['route']} | {f(r['critical_p99'],'.1f')} | {f(r['best_effort_p99'],'.0f')} | {f(r['throughput'],'.5f')} | "
                         f"{f(r['critical_miss_pct'],'.2f')} | {f(r['be_delivered_frac'],'.3f')} | {f(r['switched_pct'],'.1f')} | {r['deadlocked_seeds']} |")
        lines.append('')
    (OUT/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
