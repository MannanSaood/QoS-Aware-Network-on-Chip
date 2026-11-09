"""Pre-registered G4 evaluator (written and hashed into results/saqr_study/g4/protocol.json
before any held-out run). Applies CHR_OE_CANDIDATE_SPEC.md §8 margins with the
SAQR_SPEC_V2.md §9 additions to each candidate. Margins are constants here and
are not changed after data is seen.

Paired unit = seed (same trace across routes), n = 5, two-sided t 95% bounds.
Relative bounds are the paired mean difference ± t·s/√n divided by the reference mean.

Criteria (weighted mode; age mode is the matched control and only reported):
 C1 uniform, all meshes, loads where XY critical pending growth <= 1% of
    generated critical packets (pooled over seeds):
      throughput lower bound (c-xy)/xy > -3%;
      critical p99 upper bound (c-xy) < max(10% xy, 5 cycles);
      best-effort p99 upper bound (c-xy) < max(10% xy, 10 cycles).
 C2 transpose, k = 8 and 16, loads where XY mean critical miss > 5%:
      critical miss upper bound (c - best-miss comparator) < 1 percentage point;
      throughput lower bound vs the highest-throughput comparator > -3%.
    (Comparators = every non-candidate route: xy, oefixed, dyad, topsis, duato, westfirst.)
 C2h hotspot families, k = 8 and 16, all loads (SAQR §9 "difficult traffic"):
      throughput lower bound vs the highest-throughput comparator > -3%;
      critical p99 upper bound vs the lowest-p99 comparator < max(10%, 5 cycles).
 C3 hotspot families and bursty, all meshes, all loads, vs XY with the C1 margins.
    Failures at hotspot loads above sink capacity (grid value > 1) are tagged
    'beyond-sink' and listed separately; they are not counted as passes.
 C4 hidden costs, reported: best-effort delivered fraction, critical pending growth
    and oldest pending age vs XY (paired regressions listed).
 C6 safety: zero integrity errors and zero failed runs.
 k = 32 transpose: reported, no pass/fail (C2 does not apply there).
"""
import csv
import json
import math
import sys
from collections import defaultdict
from chr_common import SAQR_STUDY

G4=SAQR_STUDY/'g4'
T95={2:12.706,3:4.303,4:3.182,5:2.776}
THR_MARGIN=-3.0; P99_REL=.10; CRIT_ABS=5; BE_ABS=10; MISS_PP=1.0; XY_PENDING=.01; XY_MISS=5.0
HOT=('hotspot_corner','hotspot_edge','hotspot_center')

def metrics(r):
    k=r['k']; c,b=r['qos']['classes']; elig=c['target_eligible_packets']
    return dict(throughput=(c['ejected_flits']+b['ejected_flits'])/(r['cycles']*k*k),
                crit_p99=c['latency_p99_cycles'],be_p99=b['latency_p99_cycles'],
                crit_miss=100*c['target_missed_packets']/elig if elig else 0.0,
                crit_growth=c['pending_end']-c['pending_start'],crit_generated=c['generated_packets'],
                be_frac=b['delivered_packets']/max(1,b['generated_packets']+b['pending_start']),
                crit_oldest=c['oldest_pending_age_cycles'],be_oldest=b['oldest_pending_age_cycles'],
                integrity=r['qos']['integrity_errors'])

def paired(a,b):
    d=[x-y for x,y in zip(a,b)]; n=len(d); m=sum(d)/n
    s=math.sqrt(sum((x-m)**2 for x in d)/(n-1)) if n>1 else math.nan
    h=T95.get(n,1.96)*s/math.sqrt(n); ref=sum(b)/n
    return dict(diff=m,lo=m-h,hi=m+h,ref_mean=ref,rel=100*m/ref if ref else math.nan,
                rel_lo=100*(m-h)/ref if ref else math.nan,rel_hi=100*(m+h)/ref if ref else math.nan)

def main():
    proto=json.loads((G4/'protocol.json').read_text())
    routes=list(proto['variants']); cands=proto['candidates']; comps=[r for r in routes if r not in cands]
    seeds=proto['seeds']
    data={}; missing=defaultdict(int); integrity=0
    for c in proto['cases']:
        for mode in proto['modes']:
            for route in routes:
                f=G4/'cases'/c['name']/f'{mode}_{route}'/'result.json'
                if not f.exists(): missing[c['k']]+=1; continue
                m=metrics(json.loads(f.read_text())); integrity+=m['integrity']
                data[(c['k'],c['traffic'],c['index'],mode,route,c['seed'])]=m
    meshes=[k for k in proto['meshes'] if missing[k]==0]
    loads={(c['k'],c['traffic'],c['index']):c['load'] for c in proto['cases']}
    prog=json.loads((G4/'progress.json').read_text()) if (G4/'progress.json').exists() else {}
    failed=sum(len(v.get('failures',[])) for v in prog.values() if isinstance(v,dict))

    def col(k,t,i,mode,route,m): return [data[(k,t,i,mode,route,s)][m] for s in seeds]
    def mean(k,t,i,mode,route,m): v=col(k,t,i,mode,route,m); return sum(v)/len(v)

    # summary + full paired table (both modes)
    summ=[]; pair=[]
    for (k,t,i) in sorted(loads):
        if k not in meshes: continue
        for mode in proto['modes']:
            for route in routes:
                row=dict(k=k,traffic=t,index=i,load=loads[(k,t,i)],mode=mode,route=route)
                for m in ('throughput','crit_p99','be_p99','crit_miss','be_frac','crit_growth','crit_oldest','be_oldest'):
                    row[m]=mean(k,t,i,mode,route,m)
                summ.append(row)
            for cnd in cands:
                for ref in comps:
                    for m in ('throughput','crit_p99','be_p99','crit_miss','be_frac'):
                        pair.append(dict(k=k,traffic=t,index=i,mode=mode,candidate=cnd,ref=ref,metric=m,
                                         **paired(col(k,t,i,mode,cnd,m),col(k,t,i,mode,ref,m))))
    for name,rows in (('summary.csv',summ),('paired.csv',pair)):
        if rows:
            with (G4/name).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    W='weighted'
    checks=defaultdict(list)   # (cand, criterion) -> list of dict(where, metric, value, limit, ok, tag)
    def add(cnd,crit,where,metric,value,limit,ok,tag=''):
        checks[(cnd,crit)].append(dict(where=where,metric=metric,value=value,limit=limit,ok=bool(ok),tag=tag))
    def vs_xy(cnd,crit,k,t,i,tag=''):
        where=f'k{k} {t} l{i} ({loads[(k,t,i)]:.4g})'
        p=paired(col(k,t,i,W,cnd,'throughput'),col(k,t,i,W,'xy','throughput'))
        add(cnd,crit,where,'throughput lb % vs xy',p['rel_lo'],THR_MARGIN,p['rel_lo']>THR_MARGIN,tag)
        p=paired(col(k,t,i,W,cnd,'crit_p99'),col(k,t,i,W,'xy','crit_p99')); lim=max(P99_REL*p['ref_mean'],CRIT_ABS)
        add(cnd,crit,where,'crit p99 ub cycles vs xy',p['hi'],lim,p['hi']<lim,tag)
        p=paired(col(k,t,i,W,cnd,'be_p99'),col(k,t,i,W,'xy','be_p99')); lim=max(P99_REL*p['ref_mean'],BE_ABS)
        add(cnd,crit,where,'BE p99 ub cycles vs xy',p['hi'],lim,p['hi']<lim,tag)

    for cnd in cands:
        for (k,t,i) in sorted(loads):
            if k not in meshes: continue
            where=f'k{k} {t} l{i} ({loads[(k,t,i)]:.4g})'
            if t=='uniform':
                g=sum(col(k,t,i,W,'xy','crit_growth')); n=sum(col(k,t,i,W,'xy','crit_generated'))
                if n and g<=XY_PENDING*n: vs_xy(cnd,'C1',k,t,i)
            if t=='transpose' and k in (8,16) and mean(k,t,i,W,'xy','crit_miss')>XY_MISS:
                bm=min(comps,key=lambda r:mean(k,t,i,W,r,'crit_miss')); bt=max(comps,key=lambda r:mean(k,t,i,W,r,'throughput'))
                p=paired(col(k,t,i,W,cnd,'crit_miss'),col(k,t,i,W,bm,'crit_miss'))
                add(cnd,'C2',where,f'crit miss ub pp vs {bm}',p['hi'],MISS_PP,p['hi']<MISS_PP)
                p=paired(col(k,t,i,W,cnd,'throughput'),col(k,t,i,W,bt,'throughput'))
                add(cnd,'C2',where,f'throughput lb % vs {bt}',p['rel_lo'],THR_MARGIN,p['rel_lo']>THR_MARGIN)
            if t in HOT and k in (8,16):
                bt=max(comps,key=lambda r:mean(k,t,i,W,r,'throughput')); bp=min(comps,key=lambda r:mean(k,t,i,W,r,'crit_p99'))
                p=paired(col(k,t,i,W,cnd,'throughput'),col(k,t,i,W,bt,'throughput'))
                add(cnd,'C2h',where,f'throughput lb % vs {bt}',p['rel_lo'],THR_MARGIN,p['rel_lo']>THR_MARGIN)
                p=paired(col(k,t,i,W,cnd,'crit_p99'),col(k,t,i,W,bp,'crit_p99')); lim=max(P99_REL*p['ref_mean'],CRIT_ABS)
                add(cnd,'C2h',where,f'crit p99 ub cycles vs {bp}',p['hi'],lim,p['hi']<lim)
            if t in HOT or t=='bursty':
                vs_xy(cnd,'C3',k,t,i,tag='beyond-sink' if t in HOT and i>=6 else '')
            for m,label in (('be_frac','BE delivered fraction'),('crit_oldest','crit oldest pending age'),('crit_growth','crit pending growth')):
                p=paired(col(k,t,i,W,cnd,m),col(k,t,i,W,'xy',m))
                worse=p['hi']<0 if m=='be_frac' else p['lo']>0
                if worse: add(cnd,'C4',where,f'{label} vs xy (regression)',p['diff'],0,False)

    lines=['# SAQR G4 held-out evaluation: verdict','',
           f'Held-out seeds {seeds}. Meshes complete: {meshes}; incomplete or not run: '
           f'{[k for k in proto["meshes"] if k not in meshes]}. Binary {proto["saqr_binary_sha256"][:16]}.',
           f'Safety (C6): integrity errors {integrity}, failed runs {failed}.','',
           'Criteria are pre-registered in scripts/evaluate_saqr_g4.py (hash in protocol.json). C4 lists regressions only (reported, not pass/fail).','',
           '| candidate | criterion | checks | pass | fail | fail (beyond-sink) |','|---|---|---:|---:|---:|---:|']
    for cnd in cands:
        for crit in ('C1','C2','C2h','C3','C4'):
            v=checks.get((cnd,crit),[])
            lines.append(f"| {cnd} | {crit} | {len(v)} | {sum(x['ok'] for x in v)} | "
                         f"{sum(not x['ok'] and x['tag']!='beyond-sink' for x in v)} | {sum(not x['ok'] and x['tag']=='beyond-sink' for x in v)} |")
    lines.append('')
    for cnd in cands:
        for crit in ('C1','C2','C2h','C3','C4'):
            fails=[x for x in checks.get((cnd,crit),[]) if not x['ok']]
            if not fails: continue
            lines+=[f'## {cnd}: {crit} failures','','| where | metric | value | limit | tag |','|---|---|---:|---:|---|']
            lines+=[f"| {x['where']} | {x['metric']} | {x['value']:.2f} | {x['limit']:.2f} | {x['tag']} |" for x in fails]
            lines.append('')
    (G4/'G4_VERDICT.md').write_text('\n'.join(lines)+'\n')
    (G4/'g4_checks.json').write_text(json.dumps({f'{a}|{b}':v for (a,b),v in checks.items()},indent=1)+'\n')
    print('\n'.join(lines[:12+len(cands)*5]))

if __name__=='__main__': main()
