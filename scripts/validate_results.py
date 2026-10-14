"""Check completeness and physical/statistical invariants of the report datasets."""
import csv
import argparse
import itertools
import json
import math
from run_experiments import ROOT,execution_profile

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--include-legacy-scaling',action='store_true')
    args=parser.parse_args()
    studies=[('scaling',[4,8,16,32],[.05,.3],['uniform','hotspot'],500,1000),
             ('transpose_load',[8],[.05,.1,.2,.3,.4,.5],['transpose'],1000,3000),
             ('workloads',[8],[.05,.1,.2,.3,.4,.5],['uniform','bursty','hotspot_corner','hotspot_edge','hotspot_center'],1000,3000)]
    if args.include_legacy_scaling:
        studies.append(('traffic_scaling',[4,16,32],[.2],['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center'],1000,3000))
    checks=[]
    for study,sizes,loads,traffic,warmup,cycles in studies:
        with (ROOT/'results'/study/'metrics.csv').open() as f: rows=list(csv.DictReader(f))
        engines=['booksim'] if study=='traffic_scaling' else ['booksim','ns2']
        expected=set(itertools.product(engines,['xy','dyad','topsis'],sizes,loads,traffic,[1,2,3]))
        actual=set()
        for r in rows:
            key=(r['simulator'],r['algorithm'],int(r['mesh_k']),float(r['offered_flits_per_node_cycle']),r['traffic'],int(r['seed']))
            assert key not in actual,('duplicate',study,key)
            actual.add(key); assert r['status']=='ok',(study,key,r['status'])
            assert r['execution_profile']==execution_profile(r['simulator'],r['traffic']),('obsolete traffic configuration',study,key)
            assert int(r['warmup_cycles'])==warmup and int(r['measurement_cycles'])==cycles
            assert int(r['delivered_packets'])>0
            percentiles=[float(r[f'latency_p{p}_cycles']) for p in [50,90,95,99]]
            assert all(math.isfinite(v) and v>=0 for v in percentiles) and percentiles==sorted(percentiles)
            k=int(r['mesh_k']); assert int(r['nodes'])==k*k and int(r['physical_directed_links'])==4*k*(k-1)
            for metric in ['buffer_occupancy_pct','congested_port_time_pct','link_utilization_pct','peak_link_utilization_pct']:
                assert 0<=float(r[metric])<=100.001,(key,metric)
            assert float(r['link_utilization_pct'])<=float(r['peak_link_utilization_pct'])+1e-7
            throughput=int(r['delivered_packets'])*int(r['packet_flits'])/(k*k*cycles)
            assert math.isclose(throughput,float(r['throughput_flits_per_node_cycle']))
            if r['simulator']=='booksim' and r['traffic']=='hotspot':
                assert throughput*k*k<=1+int(r['packet_flits'])/cycles+1e-9
        assert actual==expected,(study,len(expected-actual),len(actual-expected))
        checks.append(dict(study=study,runs=len(rows),complete=True,invariants_pass=True))
    output=ROOT/'results/validation/datasets.json'; output.write_text(json.dumps(checks,indent=2)+'\n')
    print('PASS:',checks)

if __name__=='__main__': main()
