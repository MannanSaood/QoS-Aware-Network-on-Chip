"""Validate actual simulator evidence and prepare the corrected comparison charts."""
from collections import defaultdict
import argparse
import csv
import hashlib
import itertools
import json
import math
import numpy as np
from scipy.stats import t as student_t
from run_experiments import ROOT, booksim_traffic_config
from run_fair_grid import OUT,SIZES,TRAFFIC,SEEDS,WARMUP,CYCLES,loads
from prepare_primary_results import ALGS,METRICS,LABELS,EXTRAS

NAMES={'xy':'XY','dyad':'DyAD-OE (adapted)','topsis':'TOPSIS-OE (project)'}

REPORT=ROOT/'results/fair_report'

def write_csv(path,records):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=records[0]); w.writeheader(); w.writerows(records)

def main():
    global REPORT
    parser=argparse.ArgumentParser(); parser.add_argument('--meshes',type=int,nargs='+',choices=SIZES,default=SIZES)
    sizes=sorted(set(parser.parse_args().meshes))
    if sizes!=SIZES: REPORT=ROOT/'results/fair_preview'
    spec=json.loads((OUT/'protocol.json').read_text())
    rows=json.loads((OUT/'metrics.json').read_text())
    rows=[r for r in rows if r['mesh_k'] in sizes]
    expected={(k,l,tr,a,s) for k,tr,a,s in itertools.product(sizes,TRAFFIC,ALGS,SEEDS) for l in loads(k,tr)}
    actual=set(); groups=defaultdict(list); configs=defaultdict(set); diagnostics=[]
    for r in rows:
        k=r['mesh_k']; l=r['offered_flits_per_node_cycle']; tr=r['traffic']; a=r['algorithm']; s=r['seed']
        key=(k,l,tr,a,s); assert key not in actual; actual.add(key)
        assert r['status']=='ok' and r['simulator']=='booksim'
        assert r['binary_sha256']==spec['binary_sha256']
        assert r['warmup_cycles']==WARMUP and r['measurement_cycles']==CYCLES
        assert r['nodes']==k*k and r['packet_flits']==5
        stem=f'booksim_{a}_k{k}_{tr}_l{l}_s{s}'
        raw=OUT/'cases'/f'k{k}_{tr}_l{l}_s{s}'/'raw'
        evidence=json.loads((raw/(stem+'.json')).read_text()); assert r==evidence
        metrics=json.loads((raw/(stem+'.metrics.json')).read_text())
        assert all(r[m]==v for m,v in metrics.items())
        config=(raw/(stem+'.cfg')).read_text()
        pattern,injection=booksim_traffic_config(k,tr)
        for required in [f'traffic = {pattern};',f'injection_process = {injection};',f'injection_rate = {l/5};',
                         'num_vcs = 4; vc_buf_size = 8;', 'routing_delay = 1;', f'routing_function = noc_{a};']:
            assert required in config,(key,required)
        configs[k,l,tr,s].add(config.replace(f'noc_{a}','noc_POLICY'))
        quantiles=[r[f'latency_p{p}_cycles'] for p in [50,90,95,99]]
        assert all(math.isfinite(v) and v>=0 for v in quantiles) and quantiles==sorted(quantiles)
        assert r['delivered_packets']>0 and r['physical_directed_links']==4*k*(k-1)
        assert r['first_half_delivered_packets']+r['second_half_delivered_packets']==r['delivered_packets']
        assert math.isclose(r['throughput_flits_per_node_cycle'],r['delivered_packets']*5/(k*k*CYCLES))
        for m in ['buffer_occupancy_pct','congested_port_time_pct','peak_link_utilization_pct','link_utilization_pct']:
            assert 0<=r[m]<=100.001
        first=r['first_half_delivered_packets']; second=r['second_half_delivered_packets']
        pfirst=r['first_half_p99_cycles']; psecond=r['second_half_p99_cycles']
        drift=psecond>1.25*pfirst or abs(second-first)>.1*first
        diagnostics.append(dict(mesh_k=k,traffic=tr,load=l,algorithm=a,seed=s,
            first_half_p99=pfirst,second_half_p99=psecond,
            first_half_throughput=first*5/(k*k*(CYCLES//2)),second_half_throughput=second*5/(k*k*(CYCLES//2)),
            temporal_drift_flag=drift,low_packet_count=r['delivered_packets']<1000,
            delivered_packets=r['delivered_packets'],throughput_offered_pct=r['throughput_offered_pct']))
        groups[key[:-1]].append(r)
    assert actual==expected, f'Incomplete: {len(actual)}/{len(expected)}'
    assert all(len(v)==1 for v in configs.values()),'Resources/traffic differ between algorithms'
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'figure_verification.json').write_text(json.dumps(dict(complete_study=False,
        measured_runs=len(rows),checks_passed=False,status='pending_export_and_verification'),indent=2)+'\n')
    write_csv(REPORT/'measured_runs.csv',rows); write_csv(REPORT/'diagnostics.csv',diagnostics)
    summary=[]; index={}
    for key,seed_rows in sorted(groups.items()):
        k,l,tr,a=key
        for metric in list(METRICS)+EXTRAS:
            values=np.array([r[metric] for r in seed_rows]); assert len(values)==len(SEEDS) and np.all(np.isfinite(values))
            rec=dict(mesh_k=k,load=l,traffic=tr,algorithm=a,metric=metric,n=len(values),mean=float(values.mean()),
                ci95_halfwidth=float(student_t.ppf(.975,len(values)-1)*values.std(ddof=1)/np.sqrt(len(values))))
            summary.append(rec); index[(*key,metric)]=rec
    write_csv(REPORT/'summary.csv',summary)
    leaders=[]; comparisons=[]
    for k,tr in itertools.product(sizes,TRAFFIC):
        for l,metric in itertools.product(loads(k,tr),METRICS):
            means={a:index[k,l,tr,a,metric]['mean'] for a in ALGS}
            best=(max if metric=='throughput_flits_per_node_cycle' else min)(means.values())
            leaders.append(dict(mesh_k=k,load=l,traffic=tr,metric=metric,
                descriptive_leader=' / '.join(NAMES[a] for a,v in means.items() if math.isclose(v,best,rel_tol=1e-9,abs_tol=1e-12)),
                **{a+'_mean':means[a] for a in ALGS}))
            for a in ALGS[1:]:
                comparisons.append(dict(mesh_k=k,load=l,traffic=tr,metric=metric,algorithm=a,
                    xy_mean=means['xy'],policy_mean=means[a],
                    change_of_means_pct=100*(means[a]/means['xy']-1) if means['xy'] else ''))
    write_csv(REPORT/'descriptive_leaders.csv',leaders); write_csv(REPORT/'relative_to_xy.csv',comparisons)
    def panel(k,tr,metric):
        grid=loads(k,tr); lines=[]
        for a in ALGS:
            records=[index[k,l,tr,a,metric] for l in grid]
            lines.append(dict(label=NAMES[a],algorithm=a,x=[l*100 for l in grid],
                mean=[r['mean'] for r in records],ci95=[r['ci95_halfwidth'] for r in records]))
        title=LABELS[tr]
        if tr=='hotspot_corner': title+=' (0,0)'
        elif tr=='hotspot_edge': title+=f' ({k//2},0)'
        elif tr=='hotspot_center': title+=f' ({k//2},{k//2})'
        flags=[d for d in diagnostics if d['mesh_k']==k and d['traffic']==tr]
        ylabel=METRICS[metric]+(' — log scale' if metric=='latency_p99_cycles' else '')
        return dict(title=title,traffic=tr,mesh_k=k,metric=metric,ylabel=ylabel,series=lines,
                    yscale='log' if metric=='latency_p99_cycles' else 'linear',
                    xlim=[grid[0]*100,grid[-1]*100],drift_runs=sum(d['temporal_drift_flag'] for d in flags))
    figures=[panel(k,tr,m) for k,tr,m in itertools.product(sizes,TRAFFIC,METRICS)]
    pages=[]
    for k in sizes:
        for metric,title in [('latency_p99_cycles','p99 packet latency'),('throughput_flits_per_node_cycle','Delivered throughput')]:
            pages.append(dict(title=f'{k}×{k} mesh: {title}',mesh_k=k,metric=metric,stem=f'k{k}_{metric}',
                panels=[panel(k,tr,metric) for tr in TRAFFIC]))
    for k in [k for k in [4,32] if k in sizes]:
        m='congested_port_time_pct'
        pages.append(dict(title=f'{k}×{k} mesh: congestion',mesh_k=k,metric=m,stem=f'k{k}_{m}',panels=[panel(k,tr,m) for tr in TRAFFIC]))
    for name,data in [('figure_data.json',figures),('slide_data.json',pages)]:
        (REPORT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    receipt=dict(complete=sizes==SIZES,completed_meshes=sizes,runs=len(rows),checks_passed=True,binary_sha256=spec['binary_sha256'],
        source_csv_sha256=hashlib.sha256((OUT/'metrics.csv').read_bytes()).hexdigest(),
        seeds=SEEDS,warmup_cycles=WARMUP,measurement_cycles=CYCLES,individual_chart_library_count=len(figures),
        comparison_pages=len(pages),temporal_drift_runs=sum(d['temporal_drift_flag'] for d in diagnostics),
        low_packet_count_runs=sum(d['low_packet_count'] for d in diagnostics))
    (REPORT/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (REPORT/'README.md').write_text('''# Corrected, longer BookSim comparison

1,944 actual runs; four meshes, six traffic cases, nine load points, three policies and three seeds.
Each run: 5,000 warm-up + 20,000 measurement cycles. DyAD now uses the busiest VC for its 60% trigger.
TOPSIS weights remain 0.7/0.3. See ../../docs/FAIR_COMPARISON_PROTOCOL.md for the full predeclared protocol.

72 individual line charts have seed-level 95% t-intervals; 10 six-panel comparison pages cover the agreed
presentation layout without editing any PPT. Axes retain actual fractional injection percentages and
vary by panel. P99 has a labeled logarithmic y-axis to show low-load latency and overload on one
chart; throughput and congestion have linear axes starting at zero. There are no markers,
artificial curve offsets or tuned winning thresholds.

Latency is finite-window, completed-packet latency, NOT an uncensored steady-state estimate.
diagnostics.csv records half-window throughput/p99 drift and small-sample flags; longer runs alone do
not prove stationarity. Throughput and congestion must be read alongside latency. Congestion excludes
source backlog, and lower congestion is not automatically better if delivery is also lower.
descriptive_leaders.csv is a ranking of means, not a statistical significance or equivalence claim.
Matched seeds are not identical packet trace replay. Full raw evidence is under ../fair_comparison/cases.
The previous 2,160-run study is preserved separately and must not be pooled with this changed implementation.
''',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    if sizes!=SIZES:
        (REPORT/'README.md').write_text(f'# Partial preview\n\nOnly completed meshes {sizes}; {len(rows)} measured runs. This is not the full four-mesh study. Protocol: ../../docs/FAIR_COMPARISON_PROTOCOL.md.\n',encoding='utf-8')

if __name__=='__main__': main()
