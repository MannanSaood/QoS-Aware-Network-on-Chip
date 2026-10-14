"""Traffic-organized, one-metric line figures from actual simulator CSVs.

MATLAB and Python use the same serialized seed summaries. No offsets, smoothing,
interpolated samples or artificial separation of overlapping algorithms.
"""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.stats import t
from run_experiments import ROOT,execution_profile

METRICS=[('latency_p50_cycles','p50 latency (cycles)'),
         ('latency_p90_cycles','p90 latency (cycles)'),
         ('latency_p99_cycles','p99 latency (cycles)'),
         ('throughput_flits_per_node_cycle','Throughput (flits/node/cycle)'),
         ('congested_port_time_pct','Congested port-time (%)'),
         ('peak_link_utilization_pct','Peak link utilization (%)')]
NAMES={'xy':'XY','dyad':'DyAD-OE','topsis':'TOPSIS-OE'}

def read(study):
    with (ROOT/'results'/study/'metrics.csv').open() as f:
        rows=list(csv.DictReader(f))
    assert all(r['execution_profile']==execution_profile(r['simulator'],r['traffic']) for r in rows),f'{study}: obsolete BookSim traffic parameters; rerun affected cases'
    return [r for r in rows if r['status']=='ok']

def series(rows,metric,xfield,label,algorithm,simulator,aggregate=False):
    rows=[r for r in rows if r['algorithm']==algorithm and r['simulator']==simulator]
    xs=sorted({float(r[xfield]) for r in rows}); means=[]; cis=[]; counts=[]
    for x in xs:
        samples=[float(r[metric])*(int(r['nodes']) if aggregate else 1)
                 for r in rows if float(r[xfield])==x]
        assert len(samples)==3, f'Expected three seeds for {label} at {x}, found {len(samples)}'
        values=np.asarray(samples); assert np.all(np.isfinite(values))
        means.append(float(values.mean())); counts.append(len(values))
        cis.append(float(t.ppf(.975,len(values)-1)*values.std(ddof=1)/np.sqrt(len(values))))
    assert len(xs)>=2, f'Need a line, not an isolated point: {label}'
    return dict(label=label,x=xs,mean=means,ci95=cis,n=counts)

def main():
    scaling=read('scaling'); sweep=read('transpose_load')+read('workloads')
    traffic_scaling=read('traffic_scaling')+[r for r in sweep if r['simulator']=='booksim' and float(r['offered_flits_per_node_cycle'])==.2]
    out=ROOT/'results/report'; out.mkdir(parents=True,exist_ok=True)
    figures=[]
    traffic_names={'uniform':'Uniform','transpose':'Transpose','bursty':'Bursty on/off',
                   'hotspot_corner':'Hotspot 1: corner (0,0)',
                   'hotspot_edge':'Hotspot 2: edge (4,0)',
                   'hotspot_center':'Hotspot 3: center (4,4)'}
    for ti,(traffic,name) in enumerate(traffic_names.items(),1):
        group=[r for r in sweep if r['traffic']==traffic and int(r['mesh_k'])==8]
        for mi,(metric,label) in enumerate(METRICS,1):
            lines=[series(group,metric,'offered_flits_per_node_cycle',NAMES[a],a,'booksim') for a in NAMES]
            assert all(s['x']==[.05,.1,.2,.3,.4,.5] for s in lines),'Incomplete load sweep'
            figures.append(dict(stem=f'{ti:02d}_{traffic}_{mi:02d}_{metric}',title=f'{name} — {label.split(" (")[0]}',
                context='BookSim | 8×8 mesh | 1,000 warm-up + 3,000 measured cycles',
                xlabel='Offered load (flits/node/cycle)',ylabel=label,xmesh=False,reference=None,
                caption=['Typical packet delay.','Slow packets: 90% of completed packets finish within this latency.',
                         'Tail delay: read with throughput; unfinished packets are excluded.',
                         'Useful delivered rate. Flattening below offered load indicates limited service capacity.',
                         'Fraction of sampled input ports at least 60% full; explains congestion, not packet loss.',
                         'Busiest physical inter-router link. Lower utilization alone does not mean better performance.'][mi-1],
                series=lines))
    for traffic,name in traffic_names.items():
        group=[r for r in traffic_scaling if r['traffic']==traffic]
        for i,(metric,label) in enumerate([METRICS[2],METRICS[3]],1):
            lines=[series(group,metric,'mesh_k',NAMES[a],a,'booksim') for a in NAMES]
            assert all(s['x']==[4,8,16,32] for s in lines),'Incomplete size sweep'
            figures.append(dict(stem=f'07_scaling_{traffic}_{i:02d}_{metric}',title=f'{name.split(" (")[0]} — {label.split(" (")[0]} scaling',
                context='BookSim | offered load 0.2 flits/node/cycle | 16 to 1,024 routers',
                xlabel='Mesh size (routers)',ylabel=label,xmesh=True,reference=None,
                caption='Fixed per-node load; 1,000 warm-up + 3,000 measured cycles. Arrival-conditioned latency; read with throughput.',
                series=lines))
    group=[r for r in scaling if r['traffic']=='hotspot' and float(r['offered_flits_per_node_cycle'])==.3]
    figures.append(dict(stem='08_hotspot_model_capacity',title='Hotspot throughput exposes the model difference',
        context='XY routing | all-to-one traffic | offered load 0.3 flits/node/cycle',
        xlabel='Mesh size (routers)',ylabel='Aggregate throughput (flits/cycle)',xmesh=True,reference=1.0,
        caption='Dashed reference: one-flit/cycle destination ejection capacity. This NS-2 model omits that shared server.',
        series=[series(group,'throughput_flits_per_node_cycle','mesh_k',name,'xy',engine,True)
                for engine,name in [('booksim','BookSim'),('ns2','NS-2 packet model')]]))
    (out/'figures.json').write_text(json.dumps(figures,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    index=['# College report: traffic conditions and scaling','',
           'BookSim is the primary NoC model. Six one-metric line figures per condition compare all three policies. The three hotspot locations are separate cases. For each condition two selected metrics (p99 and throughput) also show mesh scaling; one fixed-XY simulator-capacity figure completes the library.',
           '', 'Use the p99 and throughput figures in a short presentation; keep p50, p90, congestion and peak-link plots available for the corresponding analysis. This is a 49-figure library, not a 49-slide presentation.',
           '','Use the MATLAB PDFs for the report. Shading is the 95% t-interval across three seed-level means/percentiles. These are finite-window pilots, not steady-state saturation estimates.', '']
    for f in figures:
        index.extend([f"## {f['stem']}",f['caption'],
                      f"[MATLAB PDF](matlab_figures/{f['stem']}.pdf) · [PNG](matlab_figures/{f['stem']}.png)",''])
    index.extend(['## Why these workloads?',
        'Uniform is a balanced spatial baseline, not a universal ideal. Transpose maps (x,y) to (y,x); it is not on/off traffic. Bursty traffic has uniform destinations and independent per-source on/off transitions with probability 0.02 each way (50% duty, mean 50 cycles per state). Its long-run average offered load matches the Bernoulli cases.',
        '', 'Hotspot-location cases mix 20% traffic explicitly directed to the chosen location with 80% uniform background (which can also hit that location). Corner (0,0), edge (4,0), center (4,4) stay fixed during each run. The separate model-capacity diagnostic sends 100% of packets to the center; do not mix these experiments.',
        '', 'The complete data and SUMMARY.csv retain both simulators and all policies. NS-2 provides a secondary model comparison. Mean latency, delivered/offered ratio, and packet drops are tabulated instead of adding redundant figures. Hardware energy, area, algorithm compute time, and true steady-state saturation are not measured by these pilots.',
        '', 'Equal or overlapping curves remain equal. No vertical offsets, fabricated gaps, fitted splines or selectively edited measurements are used. XY need not lose: DyAD-OE and TOPSIS-OE are the documented project adaptations, and their turn restrictions and congestion signals can reduce performance on a given workload.'])
    (out/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    table=[]
    columns=[m for m,_ in METRICS]+['latency_mean_cycles','throughput_offered_pct','drops']
    for traffic in traffic_names:
        for sim in ['booksim','ns2']:
            for load in [.05,.1,.2,.3,.4,.5]:
                for alg in NAMES:
                    matches=[r for r in sweep if (r['traffic'],r['simulator'],float(r['offered_flits_per_node_cycle']),r['algorithm'])==(traffic,sim,load,alg)]
                    assert len(matches)==3,(traffic,sim,load,alg,len(matches))
                    table.append(dict(traffic=traffic,simulator=sim,load=load,algorithm=alg,n=3,
                                      **{m:float(np.mean([float(r[m]) for r in matches])) for m in columns}))
    with (out/'SUMMARY.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=table[0]); writer.writeheader(); writer.writerows(table)
    size_table=[]
    for traffic in traffic_names:
        for k in [4,8,16,32]:
            for alg in NAMES:
                matches=[r for r in traffic_scaling if (r['traffic'],int(r['mesh_k']),r['algorithm'])==(traffic,k,alg)]
                assert len(matches)==3
                size_table.append(dict(traffic=traffic,mesh_k=k,algorithm=alg,load=.2,n=3,
                                       **{m:float(np.mean([float(r[m]) for r in matches])) for m in columns}))
    with (out/'SCALING_SUMMARY.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=size_table[0]); writer.writeheader(); writer.writerows(size_table)
    leaders=['# Observed metric leaders by traffic and load','',
             'Descriptive means of three seeds, not significance tests. Tables below use BookSim. Read latency winners with throughput: unfinished packets can make completed-packet latency misleading. All engines and values are in SUMMARY.csv.', '',
             '| Traffic | Load | Lowest p50 | Lowest p90 | Lowest p99 | Highest throughput |',
             '|---|---:|---|---|---|---|']
    for traffic in traffic_names:
        for load in [.05,.1,.2,.3,.4,.5]:
            group=[r for r in table if (r['traffic'],r['simulator'],r['load'])==(traffic,'booksim',load)]
            cells=[]
            for metric in ['latency_p50_cycles','latency_p90_cycles','latency_p99_cycles','throughput_flits_per_node_cycle']:
                best=(max if metric.startswith('throughput') else min)(r[metric] for r in group)
                names=' / '.join(NAMES[r['algorithm']] for r in group if np.isclose(r[metric],best,rtol=1e-9,atol=1e-9))
                cells.append(f'{names} ({best:.4g})')
            leaders.append(f'| {traffic_names[traffic]} | {load:g} | '+' | '.join(cells)+' |')
    leaders.extend(['','A tiny numerical lead is not a robust advantage. The figures show uncertainty; threshold sensitivity, measurement-window length and traffic pattern can change the ordering. Congestion and utilization have no unconditional winner, so they are not ranked as quality scores.'])
    (out/'METRIC_LEADERS.md').write_text('\n'.join(leaders)+'\n',encoding='utf-8')
    relative=[]
    for row in table:
        if row['algorithm']=='xy': continue
        baseline=next(r for r in table if (r['traffic'],r['simulator'],r['load'],r['algorithm'])==(row['traffic'],row['simulator'],row['load'],'xy'))
        for metric in ['latency_p50_cycles','latency_p90_cycles','latency_p99_cycles','throughput_flits_per_node_cycle']:
            wins=ties=losses=0
            for seed in [1,2,3]:
                candidates=[r for r in sweep if (r['traffic'],r['simulator'],float(r['offered_flits_per_node_cycle']),int(r['seed']))==(row['traffic'],row['simulator'],row['load'],seed)]
                value=float(next(r[metric] for r in candidates if r['algorithm']==row['algorithm']))
                xy=float(next(r[metric] for r in candidates if r['algorithm']=='xy'))
                better=value>xy if metric.startswith('throughput') else value<xy
                if np.isclose(value,xy,rtol=1e-9,atol=1e-9): ties+=1
                elif better: wins+=1
                else: losses+=1
            relative.append(dict(traffic=row['traffic'],simulator=row['simulator'],load=row['load'],
                                 algorithm=row['algorithm'],metric=metric,xy_mean=baseline[metric],algorithm_mean=row[metric],
                                 change_vs_xy_pct=100*(row[metric]/baseline[metric]-1) if baseline[metric] else '',
                                 seed_wins=wins,seed_ties=ties,seed_losses=losses))
    with (out/'RELATIVE_TO_XY.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=relative[0]); writer.writeheader(); writer.writerows(relative)
    print(f'Prepared {len(figures)} selected figures in {out}')

if __name__=='__main__': main()
