"""Audit measured QoS rows; create compact MATLAB charts and paired controls."""
import argparse
from collections import defaultdict
import csv
import itertools
import json
import math
import statistics
from pathlib import Path
from qos_common import ROOT, sha
from run_qos_grid import matrix

ALGS=['xy','dyad','topsis']
NAMES={'xy':'XY','dyad':'DyAD-OE (adapted)','topsis':'TOPSIS-OE (project)'}
TRAFFIC=['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center']
LABELS=dict(zip(TRAFFIC,['Uniform','Transpose','Bursty on/off','Hotspot 1: corner','Hotspot 2: edge','Hotspot 3: center']))
METRICS={'latency_p99_cycles':'Critical-class p99 latency (cycles)',
         'throughput_flits_per_node_cycle':'Total throughput (flits/node/cycle)',
         'congested_port_time_pct':'Congested port-time (%)'}
T95=4.302652729911275 # two-sided 95% Student t, df=2, exactly three independent seeds

def csv_out(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)

def stats(values):
    assert len(values)==3 and all(math.isfinite(v) for v in values)
    return statistics.mean(values),T95*statistics.stdev(values)/math.sqrt(3)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--meshes',nargs='+',type=int,default=[4,8,16,32]); p.add_argument('--traffic',nargs='+',choices=TRAFFIC,default=TRAFFIC); a=p.parse_args()
    meshes=sorted(set(a.meshes)); assert set(meshes)<={4,8,16,32}
    traffic=[tr for tr in TRAFFIC if tr in a.traffic]; complete=meshes==[4,8,16,32] and traffic==TRAFFIC
    source=ROOT/'results/qos_comparison'; report=ROOT/('results/qos_report' if complete else 'results/qos_preview')
    spec=json.loads((source/'protocol.json').read_text())
    rows=[]; class_rows=[]; diagnostics=[]; groups=defaultdict(list); lookup={}
    for case in matrix():
        k=case['k']; tr=case['traffic']; load=case['load']; seed=case['seed']
        if k not in meshes or tr not in traffic: continue
        folder=source/'cases'/case['name']; tracehash=sha(folder/'demand.txt')
        demand_counts=[0,0]; warm_counts=[0,0]
        for line in (folder/'demand.txt').open():
            time,src,dst,cl=map(int,line.split()); demand_counts[cl]+=1
            if time>=5000: warm_counts[cl]+=1
        for mode,algorithm in itertools.product(['age','weighted'],ALGS):
            directory=folder/(mode+'_'+algorithm)
            r=json.loads((directory/'result.json').read_text()); q=r['qos']; agg=r['aggregate']
            assert r['binary_sha256']==spec['binary_sha256'] and r['trace_sha256']==tracehash
            assert q==json.loads((directory/'classes.json').read_text())
            assert agg==json.loads((directory/'aggregate.json').read_text())
            assert r['config_sha256']==sha(directory/'config.cfg')
            cfg=(directory/'config.cfg').read_text()
            for text in ['classes = 2;','num_vcs = 4; vc_buf_size = 8;','priority = class;',f'routing_function = noc_{algorithm};']:
                assert text in cfg
            assert r['warm']==5000 and r['cycles']==20000 and r['k']==k and r['seed']==seed
            assert r['mode']==mode and r['algorithm']==algorithm and q['integrity_errors']==0
            assert q['trace_packets']==sum(demand_counts)
            assert agg['delivered_packets']==sum(c['delivered_packets'] for c in q['classes'])
            meta=dict(mesh_k=k,traffic=tr,load=load,seed=seed,algorithm=algorithm,mode=mode)
            for cl,c in enumerate(q['classes']):
                assert c['generated_packets']==warm_counts[cl]
                assert c['generated_packets']+c['pending_start']==c['delivered_packets']+c['pending_end']
                assert c['pending_at_source']+c['pending_in_network']==c['pending_end']
                assert c['target_eligible_packets']+c['target_censored_packets']==c['generated_packets']
                assert c['target_on_time_packets']+c['target_missed_packets']==c['target_eligible_packets']
                assert c['first_half_delivered']+c['second_half_delivered']==c['delivered_packets']
                qs=[c[f'latency_p{p}_cycles'] for p in [50,90,99]]; assert qs==sorted(qs)
                eligible=c['target_eligible_packets']
                extra=dict(throughput_flits_per_node_cycle=c['ejected_flits']/(20000*k*k),
                           target_miss_pct=100*c['target_missed_packets']/eligible if eligible else None,
                           pending_growth=c['pending_end']-c['pending_start'])
                export=dict(c)
                if not c['delivered_packets']:
                    for name in ['latency_mean_cycles','latency_p50_cycles','latency_p90_cycles','latency_p99_cycles']: export[name]=None
                class_rows.append(dict(**meta,**export,**extra,latency_defined=c['delivered_packets']>0))
                diagnostics.append(dict(**meta,class_id=cl,pending_growth=extra['pending_growth'],
                    p99_drift=c['second_half_p99_cycles']>1.25*c['first_half_p99_cycles'],
                    low_completed_sample=c['delivered_packets']<1000,target_miss_pct=extra['target_miss_pct'],
                    censored=c['target_censored_packets']))
            critical,best_effort=q['classes']
            assert critical['delivered_packets']>0,'Cannot plot undefined critical p99'
            row=dict(**meta,latency_p99_cycles=critical['latency_p99_cycles'],
                     throughput_flits_per_node_cycle=sum(c['ejected_flits'] for c in q['classes'])/(20000*k*k),
                     congested_port_time_pct=agg['congested_port_time_pct'],
                     best_effort_p99_cycles=best_effort['latency_p99_cycles'] if best_effort['delivered_packets'] else math.nan,
                     critical_target_miss_pct=100*critical['target_missed_packets']/critical['target_eligible_packets'] if critical['target_eligible_packets'] else math.nan,
                     pending_growth=sum(c['pending_end']-c['pending_start'] for c in q['classes']),
                     aggregate_p99_cycles=agg['latency_p99_cycles'],wall_seconds=r['wall_seconds'])
            rows.append(row); groups[k,tr,load,algorithm,mode].append(row)
            lookup[k,tr,load,algorithm,mode,seed]=row
    assert len(rows)==len(meshes)*len(traffic)*162
    report.mkdir(parents=True,exist_ok=True)
    (report/'figure_verification.json').write_text(json.dumps(dict(complete_study=False,
        measured_runs=len(rows),checks_passed=False,status='pending_export_and_verification'),indent=2)+'\n')
    csv_out(report/'measured_runs.csv',rows); csv_out(report/'per_class_runs.csv',class_rows); csv_out(report/'diagnostics.csv',diagnostics)
    class_groups=defaultdict(list)
    for row in class_rows:
        class_groups[row['mesh_k'],row['traffic'],row['load'],row['algorithm'],row['mode'],row['class_id']].append(row)
    class_summary=[]
    for key,rs in sorted(class_groups.items()):
        k,tr,load,algorithm,mode,cl=key
        for metric in ['latency_mean_cycles','latency_p50_cycles','latency_p90_cycles','latency_p99_cycles',
                       'throughput_flits_per_node_cycle','target_miss_pct','pending_growth',
                       'pending_at_source','pending_in_network','oldest_pending_age_cycles','within_class_delivery_fairness']:
            values=[r[metric] for r in rs if r[metric] is not None and math.isfinite(r[metric])]
            mean,ci=stats(values) if len(values)==3 else (None,None)
            class_summary.append(dict(mesh_k=k,traffic=tr,load=load,algorithm=algorithm,mode=mode,class_id=cl,
                class_name='critical' if cl==0 else 'best_effort',metric=metric,n_defined=len(values),n_runs=3,
                mean=mean,ci95_halfwidth=ci,target_is_deadline=cl==0))
    csv_out(report/'per_class_summary.csv',class_summary)
    summary=[]; index={}; paired=[]
    for key,rs in sorted(groups.items()):
        k,tr,load,algorithm,mode=key
        for metric in [*METRICS,'best_effort_p99_cycles','critical_target_miss_pct','pending_growth','aggregate_p99_cycles']:
            vals=[r[metric] for r in rs]
            if not all(math.isfinite(v) for v in vals): continue
            mean,ci=stats(vals)
            rec=dict(mesh_k=k,traffic=tr,load=load,algorithm=algorithm,mode=mode,metric=metric,n=3,mean=mean,ci95_halfwidth=ci)
            summary.append(rec); index[*key,metric]=rec
            if mode=='weighted':
                deltas=[lookup[k,tr,load,algorithm,'weighted',s][metric]-lookup[k,tr,load,algorithm,'age',s][metric] for s in [1,2,3]]
                if all(math.isfinite(v) for v in deltas):
                    delta,dc=stats(deltas); paired.append(dict(mesh_k=k,traffic=tr,load=load,algorithm=algorithm,metric=metric,
                        weighted_minus_control=delta,ci95_halfwidth=dc,interval_includes_zero=abs(delta)<=dc))
    csv_out(report/'summary.csv',summary); csv_out(report/'paired_qos_effect.csv',paired)
    routing_pairs=[]
    for k,tr,load,mode in sorted({(r['mesh_k'],r['traffic'],r['load'],r['mode']) for r in rows}):
        for left,right in itertools.combinations(ALGS,2):
            for metric in METRICS:
                deltas=[lookup[k,tr,load,left,mode,s][metric]-lookup[k,tr,load,right,mode,s][metric] for s in [1,2,3]]
                delta,ci=stats(deltas)
                routing_pairs.append(dict(mesh_k=k,traffic=tr,load=load,mode=mode,
                    algorithm_left=left,algorithm_right=right,metric=metric,
                    left_minus_right=delta,ci95_halfwidth=ci,interval_includes_zero=abs(delta)<=ci,n_pairs=3))
    csv_out(report/'paired_routing_differences.csv',routing_pairs)
    leaders=[]
    grids={(k,tr):sorted({c['load'] for c in spec['cases'] if c['k']==k and c['traffic']==tr}) for k,tr in itertools.product(meshes,traffic)}
    for k,tr in grids:
        for load,metric in itertools.product(grids[k,tr],METRICS):
            means={alg:index[k,tr,load,alg,'weighted',metric]['mean'] for alg in ALGS}
            value=(max if metric=='throughput_flits_per_node_cycle' else min)(means.values())
            leaders.append(dict(mesh_k=k,traffic=tr,load=load,metric=metric,
                descriptive_leader=' / '.join(NAMES[a] for a,v in means.items() if math.isclose(v,value,rel_tol=1e-9,abs_tol=1e-12)),**means))
    csv_out(report/'descriptive_leaders.csv',leaders)
    tradeoffs=['# QoS tradeoffs at the highest tested load in each case','',
        'Values are three-seed means, shown as weighted / age-only control. These are finite-window',
        'measurements and may be overloaded. Critical-tail improvements must be read with best-effort',
        'tails, total throughput, deadline misses and pending growth. No policy is declared universally better.','',
        '| Mesh | Traffic | Algorithm | Load | Critical p99 | Best-effort p99 | Total throughput | Critical target misses (%) |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for k,tr in grids:
        load=max(grids[k,tr])
        for algorithm in ALGS:
            cells=[]
            for metric in ['latency_p99_cycles','best_effort_p99_cycles','throughput_flits_per_node_cycle','critical_target_miss_pct']:
                cells.append(' / '.join(f'{index[k,tr,load,algorithm,mode,metric]["mean"]:.5g}' if (k,tr,load,algorithm,mode,metric) in index else 'undefined' for mode in ['weighted','age']))
            tradeoffs.append(f'| {k}x{k} | {tr} | {NAMES[algorithm]} | {load:.5g} | '+' | '.join(cells)+' |')
    (report/'QOS_TRADEOFFS.md').write_text('\n'.join(tradeoffs)+'\n',encoding='utf-8')
    def panel(k,tr,metric):
        grid=grids[k,tr]; title=LABELS[tr]
        if tr.startswith('hotspot'):
            xy={'hotspot_corner':(0,0),'hotspot_edge':(k//2,0),'hotspot_center':(k//2,k//2)}[tr]
            title+=f' ({xy[0]},{xy[1]})'
        series=[]
        for algorithm in ALGS:
            records=[index[k,tr,l,algorithm,'weighted',metric] for l in grid]
            series.append(dict(label=NAMES[algorithm],algorithm=algorithm,x=[100*l for l in grid],mean=[r['mean'] for r in records],ci95=[r['ci95_halfwidth'] for r in records]))
        return dict(mesh_k=k,traffic=tr,title=title,metric=metric,ylabel=METRICS[metric]+(' - log scale' if metric=='latency_p99_cycles' else ''),series=series,
                    xlim=[grid[0]*100,grid[-1]*100],yscale='log' if metric=='latency_p99_cycles' else 'linear')
    figures=[panel(k,tr,m) for k,tr,m in itertools.product(meshes,traffic,METRICS)]
    pages=[]
    for k in (meshes if traffic==TRAFFIC else []):
        for metric,title in [('latency_p99_cycles','Critical-class p99 latency'),('throughput_flits_per_node_cycle','Total delivered throughput')]:
            pages.append(dict(mesh_k=k,metric=metric,title=f'{k}x{k} mesh: {title}',stem=f'k{k}_{metric}',panels=[panel(k,tr,metric) for tr in TRAFFIC]))
    for k in [m for m in [4,32] if m in meshes and traffic==TRAFFIC]:
        metric='congested_port_time_pct'; pages.append(dict(mesh_k=k,metric=metric,title=f'{k}x{k} mesh: congestion',stem=f'k{k}_{metric}',panels=[panel(k,tr,metric) for tr in TRAFFIC]))
    for name,data in [('figure_data.json',figures),('slide_data.json',pages)]: (report/name).write_text(json.dumps(data,indent=2)+'\n')
    receipt=dict(complete=complete,runs=len(rows),warmup_cycles=5000,measurement_cycles=20000,
                 checks_passed=True,binary_sha256=spec['binary_sha256'],protocol_sha256=sha(source/'protocol.json'),
                 caption='QoS: 25% critical demand; 3:1 local class service. p99 is critical-class; throughput is total.',
                 caution='Completed-packet p99: read with per-class backlog and deadline misses in supporting tables.')
    (report/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (report/'README.md').write_text('''# QoS showcase results

Main graphs show **critical-class p99**, **total ejected-flit throughput**, and
physical congested-port time, one metric per figure. All algorithms use the same
weighted service, trace, class mix, VC partition, pipeline and resource budget.
Eight latency/throughput comparison pages cover every mesh and all six traffic
cases; two congestion pages show 4x4 and 32x32. The 72 individual charts retain
three-seed confidence intervals. Lines connect measured load points; no smoothing.

`per_class_runs.csv` retains p50/p90/p99, source/network backlog, deadline outcomes,
censored demand and within-class fairness. `paired_qos_effect.csv` compares weighted
service against the same-trace age-only control, including best-effort tradeoffs.
`descriptive_leaders.csv` reports smallest/largest sample means, not proven winners.
Confidence intervals use independent seed-level observations, not packets as replicates.
`per_class_summary.csv` supplies three-seed means/intervals for p50, p90, p99 and
the supporting QoS metrics. Undefined populations stay blank, with counts given.
`paired_routing_differences.csv` compares algorithms on the same demand traces.
Its differences are left minus right; throughput favors positive values, latency
favors negative values, and congestion needs interpretation with throughput.
Intervals are exploratory, pointwise 95% t-intervals with three seed pairs, without
multiple-comparison correction. An interval containing zero does not prove equality.

Critical deadlines are a synthetic 16*k-cycle target, not an application guarantee.
Under overload, incomplete packets are excluded from completed latency but counted
in pending demand and eligible deadline misses. Read latency with those outcomes.
No hard guarantees, energy savings, hardware speedup or SOTA claim follows from this study.

Congestion uses aggregate physical-port occupancy >=60% across four VCs. Two full
best-effort VCs plus two empty critical VCs are only 50% in this definition.
It therefore does not measure class-specific congestion. Read it with per-class
backlog and latency rather than treating a lower value as an automatic win.
''',encoding='utf-8')
    if not complete:
        readme=report/'README.md'; readme.write_text('**PARTIAL PREVIEW:** '+str(meshes)+'; '+', '.join(traffic)+'. Full-study layout described below is not yet complete.\n\n'+readme.read_text(),encoding='utf-8')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__': main()
