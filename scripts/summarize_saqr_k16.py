"""Summarize the SAQR 16x16 frontier stage. Same metric definitions and
exploratory paired t-intervals as summarize_saqr_pilot.py (tuning seeds,
pointwise, not multiplicity-adjusted)."""
import csv
import json
import math
from chr_common import SAQR_STUDY
from summarize_saqr_pilot import metrics, mean_ci

OUT=SAQR_STUDY/'stage_k16'
REFS=('xy','oefixed','dyad','topsis','duato')
CANDS=('saqr','saqr_nogate','saqr_nogate_crit')

def main():
    global OUT, CANDS
    import sys
    proto=json.loads((OUT/'protocol.json').read_text()); routes=list(proto['variants'])
    source={r:OUT for r in routes}
    if '--twotier' in sys.argv:
        tt=SAQR_STUDY/'stage_k16_twotier'; ptt=json.loads((tt/'protocol.json').read_text())
        for r in ptt['variants']: routes.append(r); source[r]=tt
        CANDS=CANDS+tuple(ptt['variants']); OUT=tt
    if '--o1t' in sys.argv:
        tt=SAQR_STUDY/'stage_k16_o1t'; ptt=json.loads((tt/'protocol.json').read_text())
        for r in ptt['variants']: routes.append(r); source[r]=tt
        CANDS=CANDS+tuple(ptt['variants']); OUT=tt
    data={}
    for c in proto['cases']:
        for route in routes:
            r=json.loads((source[route]/'cases'/c['name']/f'weighted_{route}'/'result.json').read_text())
            data[(c['traffic'],c['load'],c['seed'],route)]=metrics(r)
    keys=sorted({(t,l) for t,l,_,_ in data}); seeds=sorted({s for _,_,s,_ in data})
    names=['critical_p99','best_effort_p99','throughput','critical_miss_pct','be_delivered_frac','pending_growth','switched_pct']
    rows=[]
    for t,l in keys:
        for route in routes:
            row=dict(traffic=t,load=l,route=route)
            for m in names:
                mu,ci=mean_ci([data[(t,l,s,route)][m] for s in seeds]); row[m]=mu; row[m+'_ci']=ci
            rows.append(row)
    with (OUT/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    paired=[]
    for t,l in keys:
        for route in CANDS:
            for ref in REFS:
                for m in ('critical_p99','best_effort_p99','throughput','critical_miss_pct'):
                    pairs=[(data[(t,l,s,route)][m],data[(t,l,s,ref)][m]) for s in seeds]
                    mu,ci=mean_ci([x-y for x,y in pairs]); refm=sum(y for _,y in pairs)/len(pairs)
                    paired.append(dict(traffic=t,load=l,route=route,ref=ref,metric=m,n=len(pairs),diff=mu,ci95=ci,
                        rel_pct=100*mu/refm if refm else math.nan,rel_lo_pct=100*(mu-ci)/refm if refm else math.nan,
                        rel_hi_pct=100*(mu+ci)/refm if refm else math.nan))
    with (OUT/'paired.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired[0])); w.writeheader(); w.writerows(paired)
    f=lambda v,fmt: '—' if isinstance(v,float) and math.isnan(v) else format(v,fmt)
    lines=['# SAQR 16x16 frontier stage: exploratory summary','',
           'Weighted mode, tuning seeds 101-103 (not held out). All routes run fresh on the SAQR binary; anchor reproduced frozen 16x16 receipts exactly.',
           'Throughput = total ejected flits/node/cycle. Miss = critical target misses (%). BE frac = best-effort delivered fraction.','']
    for t in sorted({t for t,_ in keys}):
        lines+=[f'## {t}','','| load | route | crit p99 | BE p99 | throughput | crit miss % | BE frac | sw % |','|---:|---|---:|---:|---:|---:|---:|---:|']
        for r in rows:
            if r['traffic']!=t: continue
            lines.append(f"| {r['load']:.4g} | {r['route']} | {f(r['critical_p99'],'.1f')} | {f(r['best_effort_p99'],'.0f')} | {f(r['throughput'],'.5f')} | "
                         f"{f(r['critical_miss_pct'],'.2f')} | {f(r['be_delivered_frac'],'.3f')} | {f(r['switched_pct'],'.1f')} |")
        lines.append('')
    lines+=['## Paired relative differences (candidate vs reference, % of reference; 95% CI bounds)','',
            '| traffic | load | candidate | ref | throughput % [lo, hi] | crit p99 % [lo, hi] |','|---|---:|---|---|---|---|']
    idx={(p['traffic'],p['load'],p['route'],p['ref'],p['metric']):p for p in paired}
    for t,l in keys:
        for route in CANDS:
            for ref in REFS:
                a=idx[(t,l,route,ref,'throughput')]; b=idx[(t,l,route,ref,'critical_p99')]
                lines.append(f"| {t} | {l:.4g} | {route} | {ref} | {f(a['rel_pct'],'+.1f')} [{f(a['rel_lo_pct'],'+.1f')}, {f(a['rel_hi_pct'],'+.1f')}] | "
                             f"{f(b['rel_pct'],'+.1f')} [{f(b['rel_lo_pct'],'+.1f')}, {f(b['rel_hi_pct'],'+.1f')}] |")
    (OUT/'SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines[:200]))

if __name__=='__main__': main()
