"""Summarize the SAQR-SC tuning pilot and apply the selection rule fixed in
run_saqr_src_pilot.py. Tuning seeds only; no acceptance claim."""
import json
import math
from run_saqr_src_pilot import OUT, SC, BASE, K8_REF, TRAFFIC, k4_cases
from chr_common import STUDY

T=4.303   # t(0.975, 2) for 3 seeds

def metrics(r):
    k=r['k']; c,b=r['qos']['classes']; el=c['target_eligible_packets']
    m=dict(thr=(c['ejected_flits']+b['ejected_flits'])/(r['cycles']*k*k),cp99=c['latency_p99_cycles'],bp99=b['latency_p99_cycles'],
           miss=100*c['target_missed_packets']/el if el else 0.0,adapt=math.nan)
    s=(r.get('saqr') or {}).get('src')
    if s: tot=sum(map(sum,s['marked'])); m['adapt']=100*sum(x[1] for x in s['marked'])/tot if tot else 0.0
    return m

def path(c,route):
    if route in SC or c['k']==4: return OUT/'cases'/c['name']/f'weighted_{route}'/'result.json'
    return K8_REF[route]/'cases'/c['name']/f'weighted_{route}'/'result.json'

def main():
    k8=json.loads((STUDY/'pilot_k8/protocol.json').read_text())['cases']; cases=k8+k4_cases()
    routes=list(BASE)+list(SC)
    data={}
    for c in cases:
        for r in routes: data[(c['k'],c['traffic'],c['index'],r,c['seed'])]=metrics(json.loads(path(c,r).read_text()))
    keys=sorted({(c['k'],c['traffic'],c['index'],c['load']) for c in cases}); seeds=[101,102,103]
    def col(k,t,i,r,m): return [data[(k,t,i,r,s)][m] for s in seeds]
    def rel(k,t,i,a,b,m='thr'):
        x,y=col(k,t,i,a,m),col(k,t,i,b,m); d=[p-q for p,q in zip(x,y)]; mu=sum(d)/3
        sd=math.sqrt(sum((v-mu)**2 for v in d)/2); ref=sum(y)/3
        return 100*mu/ref, 100*(mu-T*sd/math.sqrt(3))/ref
    lines=['# SAQR-SC tuning pilot (seeds 101-103; not held out)','',
           'Throughput % vs reference: mean [paired lower bound]. adapt % = packets marked adaptive by the source classifier.','']
    sel={}
    for v in SC:
        if v=='sc_never': continue
        ok=all(rel(k,t,i,v,'xy')[1]>-3 for (k,t,i,_) in keys if t=='uniform')
        tr=[sum(col(k,t,i,v,'thr'))/3 for (k,t,i,_) in keys if t=='transpose']
        sel[v]=dict(c1_ok=ok,transpose_mean_thr=sum(tr)/len(tr))
    elig=[v for v in sel if sel[v]['c1_ok']]
    if elig:
        best=max(elig,key=lambda v:sel[v]['transpose_mean_thr'])
        if 'sc_128_64' in elig and sel['sc_128_64']['transpose_mean_thr']>=sel[best]['transpose_mean_thr']*0.995: best='sc_128_64'
    else: best=None
    lines+=['## Selection (rule fixed before the pilot)','','| variant | uniform C1 (lb > -3% vs XY everywhere) | mean transpose throughput |','|---|---|---:|']
    lines+=[f"| {v} | {'pass' if s['c1_ok'] else 'FAIL'} | {s['transpose_mean_thr']:.5f} |" for v,s in sel.items()]
    lines+=['',f'**Selected:** {best or "none (no variant passes the uniform rule)"}','']
    for k in (4,8):
        for t in TRAFFIC:
            lines+=[f'## k={k} {t}','','| load | route | throughput | crit p99 | BE p99 | crit miss % | adapt % | vs XY | vs o1t_both | vs best comparator |','|---:|---|---:|---:|---:|---:|---:|---|---|---|']
            for (kk,tt,i,ld) in keys:
                if kk!=k or tt!=t: continue
                comps=['xy','oefixed','dyad','topsis','duato','westfirst']
                bc=max(comps,key=lambda r:sum(col(k,t,i,r,'thr')))
                for r in routes:
                    mu=lambda m: sum(col(k,t,i,r,m))/3
                    f=lambda a: f'{a[0]:+.1f} [{a[1]:+.1f}]'
                    vs=(f(rel(k,t,i,r,'xy')) if r!='xy' else '—', f(rel(k,t,i,r,'saqr_o1t_both')) if r!='saqr_o1t_both' else '—',
                        f(rel(k,t,i,r,bc))+f' ({bc})' if r!=bc else '—')
                    ad=mu('adapt'); ad='—' if math.isnan(ad) else f'{ad:.1f}'
                    lines.append(f"| {ld:.4g} | {r} | {mu('thr'):.5f} | {mu('cp99'):.1f} | {mu('bp99'):.0f} | {mu('miss'):.2f} | {ad} | {vs[0]} | {vs[1]} | {vs[2]} |")
            lines.append('')
    (OUT/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    (OUT/'selection.json').write_text(json.dumps(dict(selection=sel,selected=best),indent=2)+'\n')
    print('\n'.join(lines[:14+len(sel)]))

if __name__=='__main__': main()
