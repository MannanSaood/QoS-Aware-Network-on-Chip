"""Validate the 2,160-run primary study and prepare editable chart data."""
import csv
import argparse
import hashlib
import io
import itertools
import json
import math
from collections import defaultdict
import numpy as np
from scipy.stats import t
from run_experiments import ROOT,execution_profile,booksim_traffic_config
from run_primary_grid import SIZES,LOADS,TRAFFIC,SEEDS

ALGS=['xy','dyad','topsis']
NAMES={'xy':'XY','dyad':'DyAD-OE','topsis':'TOPSIS-OE'}
METRICS={'latency_p99_cycles':'p99 latency (cycles)',
         'throughput_flits_per_node_cycle':'Throughput (flits/node/cycle)',
         'congested_port_time_pct':'Congested port-time (%)'}
LABELS={'uniform':'Uniform','transpose':'Transpose','bursty':'Bursty on/off',
        'hotspot_corner':'Hotspot 1: corner','hotspot_edge':'Hotspot 2: edge','hotspot_center':'Hotspot 3: center'}
EXTRAS=['latency_mean_cycles','latency_p50_cycles','latency_p90_cycles','buffer_occupancy_pct',
        'peak_link_utilization_pct','link_utilization_pct','throughput_offered_pct']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--meshes',type=int,nargs='+',choices=SIZES,default=SIZES)
    args=parser.parse_args(); sizes=sorted(set(args.meshes))
    source=ROOT/'results/primary_grid/metrics.csv'
    source_bytes=source.read_bytes()
    rows=list(csv.DictReader(io.StringIO(source_bytes.decode('utf-8'))))
    rows=[r for r in rows if int(r['mesh_k']) in sizes]
    expected=set(itertools.product(sizes,LOADS,TRAFFIC,ALGS,SEEDS)); actual=set(); groups=defaultdict(list)
    for r in rows:
        k=int(r['mesh_k']); load=float(r['offered_flits_per_node_cycle']); seed=int(r['seed'])
        key=(k,load,r['traffic'],r['algorithm'],seed)
        assert key not in actual,('duplicate',key)
        assert r['status']=='ok' and r['simulator']=='booksim',('failed run',key)
        assert r['execution_profile']==execution_profile('booksim',r['traffic']),('obsolete traffic configuration',key)
        assert int(r['warmup_cycles'])==1000 and int(r['measurement_cycles'])==3000
        assert int(r['nodes'])==k*k and int(r['packet_flits'])==5
        case=f'k{k}_{r["traffic"]}_l{load}_s{seed}'
        stem=f'booksim_{r["algorithm"]}_k{k}_{r["traffic"]}_l{load}_s{seed}'
        raw=ROOT/'results/primary_grid/cases'/case/'raw'
        config=(raw/(stem+'.cfg')).read_text()
        pattern,injection=booksim_traffic_config(k,r['traffic'])
        for required in [f'traffic = {pattern};',f'injection_process = {injection};',
                         f'routing_function = noc_{r["algorithm"]};',f'injection_rate = {load/5};']:
            assert required in config,('configuration mismatch',key,required)
        evidence=json.loads((raw/(stem+'.json')).read_text())
        for metric in ['delivered_packets','latency_p50_cycles','latency_p90_cycles','latency_p99_cycles',
                       'throughput_flits_per_node_cycle','congested_port_time_pct']:
            assert math.isclose(float(r[metric]),float(evidence[metric])),('raw evidence mismatch',key,metric)
        quantiles=[float(r[f'latency_p{p}_cycles']) for p in [50,90,95,99]]
        assert all(math.isfinite(v) and v>=0 for v in quantiles) and quantiles==sorted(quantiles)
        assert int(r['delivered_packets'])>0 and int(r['physical_directed_links'])==4*k*(k-1)
        for metric in ['buffer_occupancy_pct','congested_port_time_pct','peak_link_utilization_pct','link_utilization_pct']:
            assert 0<=float(r[metric])<=100.001
        assert math.isclose(float(r['throughput_flits_per_node_cycle']),int(r['delivered_packets'])*5/(k*k*3000))
        actual.add(key); groups[key[:-1]].append(r)
    assert actual==expected,f'Incomplete grid: {len(actual)}/{len(expected)}, missing {len(expected-actual)}'
    out=ROOT/('results/primary_report' if sizes==SIZES else 'results/primary_preview'); out.mkdir(parents=True,exist_ok=True)
    summary=[]; index={}
    for key,seed_rows in sorted(groups.items()):
        k,load,traffic,alg=key
        for metric in list(METRICS)+EXTRAS:
            values=np.asarray([float(r[metric]) for r in seed_rows]); assert len(values)==3 and np.all(np.isfinite(values))
            rec=dict(mesh_k=k,load=load,traffic=traffic,algorithm=alg,metric=metric,n=3,
                     mean=float(values.mean()),ci95_halfwidth=float(t.ppf(.975,2)*values.std(ddof=1)/np.sqrt(3)))
            summary.append(rec); index[(*key,metric)]=rec
    with (out/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=summary[0]); w.writeheader(); w.writerows(summary)
    # Pair by seed for descriptive consistency; do not infer statistical wins.
    comparisons=[]; leaders=[]
    core=['latency_p99_cycles','throughput_flits_per_node_cycle']
    for k,load,traffic in itertools.product(sizes,LOADS,TRAFFIC):
        baseline={int(r['seed']):r for r in groups[(k,load,traffic,'xy')]}
        for metric in core:
            means={alg:index[(k,load,traffic,alg,metric)]['mean'] for alg in ALGS}
            best=(min if metric=='latency_p99_cycles' else max)(means.values())
            leaders.append(dict(mesh_k=k,load=load,traffic=traffic,metric=metric,
                descriptive_leader=' / '.join(NAMES[a] for a,v in means.items() if math.isclose(v,best,rel_tol=1e-9,abs_tol=1e-12)),
                **{a+'_mean':means[a] for a in ALGS}))
            for alg in ALGS[1:]:
                changes=[]; better=equal=worse=0
                for r in groups[(k,load,traffic,alg)]:
                    x=float(baseline[int(r['seed'])][metric]); y=float(r[metric])
                    changes.append(100*(y/x-1) if x else float('nan'))
                    delta=(x-y) if metric=='latency_p99_cycles' else (y-x)
                    if math.isclose(x,y,rel_tol=1e-9,abs_tol=1e-12): equal+=1
                    elif delta>0: better+=1
                    else: worse+=1
                comparisons.append(dict(mesh_k=k,load=load,traffic=traffic,algorithm=alg,metric=metric,
                    xy_mean=means['xy'],policy_mean=means[alg],
                    change_of_means_pct=100*(means[alg]/means['xy']-1) if means['xy'] else '',
                    mean_paired_seed_change_pct=float(np.mean(changes)),
                    better_seeds=better,equal_seeds=equal,worse_seeds=worse))
    for filename,records in [('relative_to_xy.csv',comparisons),('descriptive_leaders.csv',leaders)]:
        with (out/filename).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=records[0]); w.writeheader(); w.writerows(records)
    # Archive the exact inputs: the live aggregate can grow while previews render.
    with (out/'measured_runs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    def panel(k,traffic,metric):
        lines=[]
        for alg in ALGS:
            records=[index[(k,load,traffic,alg,metric)] for load in LOADS]
            lines.append(dict(label=NAMES[alg],algorithm=alg,x=[int(x*100) for x in LOADS],
                              mean=[r['mean'] for r in records],ci95=[r['ci95_halfwidth'] for r in records]))
        title=LABELS[traffic]
        if traffic=='hotspot_corner': title+=' (0,0)'
        elif traffic=='hotspot_edge': title+=f' ({k//2},0)'
        elif traffic=='hotspot_center': title+=f' ({k//2},{k//2})'
        return dict(title=title,traffic=traffic,mesh_k=k,metric=metric,ylabel=METRICS[metric],series=lines)
    slides=[]
    for k in sizes:
        for metric,title in [('latency_p99_cycles','p99 packet latency'),('throughput_flits_per_node_cycle','Delivered throughput')]:
            slides.append(dict(title=f'{k}×{k} mesh: {title}',mesh_k=k,metric=metric,
                               stem=f'k{k}_{metric}',panels=[panel(k,traffic,metric) for traffic in TRAFFIC]))
    for k in [k for k in [4,32] if k in sizes]:
        metric='congested_port_time_pct'
        slides.append(dict(title=f'{k}×{k} mesh: congestion',mesh_k=k,metric=metric,
                           stem=f'k{k}_{metric}',panels=[panel(k,traffic,metric) for traffic in TRAFFIC]))
    (out/'slide_data.json').write_text(json.dumps(slides,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    figures=[panel(k,traffic,metric) for k in sizes for traffic in TRAFFIC for metric in METRICS]
    (out/'figure_data.json').write_text(json.dumps(figures,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    receipt=dict(runs=len(rows),complete=sizes==SIZES,completed_meshes=sizes,checks_passed=True,source_csv_sha256=hashlib.sha256(source_bytes).hexdigest(),
                 main_figure_count=2*len(sizes),congestion_figure_count=len(slides)-2*len(sizes),main_chart_count=12*len(sizes),
                 individual_chart_library_count=len(figures),congestion_figure_meshes=[k for k in [4,32] if k in sizes])
    (out/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (out/'README.md').write_text('''# Measured BookSim results

The primary grid contains 2,160 actual BookSim runs: four meshes, six traffic
cases, ten offered loads, three routing policies and three seeds. Each run has
1,000 warm-up and 3,000 observation cycles. This is a finite-window study.

`summary.csv` contains means and 95% t-intervals across seed-level statistics,
including p50/p90/p99. `slide_data.json` defines the eight main six-panel figures
and two congestion figures; it does not create or modify a presentation. The
congestion figures compare 4x4 and 32x32, each
with all six cases. `figure_data.json` retains all 72 individual p99, throughput
and congestion plots; the comparison pages select 60 of these panels.
`measured_runs.csv` preserves the exact input rows used for this report.
`relative_to_xy.csv` gives percentage differences and paired-seed consistency.
`descriptive_leaders.csv` identifies lowest mean p99 or highest mean throughput
at each measured condition. These are descriptive rankings, not significance
tests. Lower p99 may reflect unfinished packets under overload, so assess both
metrics together. Equal seed IDs match inputs, not necessarily adaptive paths.

X is nominal offered injection, 10–100% of one flit/node/cycle. It is not measured
network occupancy. p99 includes only packets completed in the observation
window; overloaded sources can retain unfinished demand. Interpret latency with
throughput. Three seeds do not establish statistical equivalence or SOTA.

Transpose is a spatial pattern, (x,y) to (y,x). Bursty is a separate 50%-duty
Markov injection process with mean 50-cycle ON/OFF durations and uniform
destinations. Mixed hotspots direct 20% of traffic to the location and 80% to
uniform destinations; location remains fixed within each run.

Line colors and styles stay consistent. No dot markers, vertical offsets,
fabricated gaps, fitted curves, or interpolation of unmeasured loads are used.
Full configurations, raw metrics and process logs remain in primary_grid/cases.
NS-2 results remain a separate, coarser model comparison in workloads,
transpose_load and scaling; they do not determine the primary algorithm rankings.
''',encoding='utf-8')
    if sizes!=SIZES:
        (out/'README.md').write_text(f'# Completed-mesh preview\n\nOnly meshes {sizes} are included. This is not the completed four-mesh study. Each included mesh has all six traffic cases, ten loads, three algorithms and three seeds.\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__': main()
