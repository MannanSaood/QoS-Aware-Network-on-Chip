"""Check actual old-window reproduction and low-load pilots before the full study."""
import json
from run_experiments import ROOT

audit=json.loads((ROOT/'results/routing_comparison_audit/runs.json').read_text())
rows=json.loads((ROOT/'results/fair_reproduction/metrics.json').read_text())
assert len(rows)==9
metrics=['delivered_packets','latency_mean_cycles','latency_p50_cycles','latency_p90_cycles','latency_p95_cycles',
         'latency_p99_cycles','mean_hops','buffer_occupancy_pct','congested_port_time_pct',
         'link_utilization_pct','peak_link_utilization_pct','physical_directed_links']
for r in rows:
    variant='dyad_peak_trigger' if r['algorithm']=='dyad' else r['algorithm']
    old=next(a for a in audit if a['traffic']=='uniform' and a['seed']==r['seed'] and a['variant']==variant)
    assert r['status']=='ok'
    for m in metrics: assert r[m]==old[m],(r['algorithm'],r['seed'],m,r[m],old[m])
    assert r['first_half_delivered_packets']+r['second_half_delivered_packets']==r['delivered_packets']
pilots=json.loads((ROOT/'results/fair_pilot/metrics.json').read_text()); assert len(pilots)==9
for r in pilots:
    assert r['status']=='ok' and r['measurement_cycles']==20000
    assert r['first_half_delivered_packets']+r['second_half_delivered_packets']==r['delivered_packets']
    assert 85<r['throughput_offered_pct']<115,(r['algorithm'],r['mesh_k'],r['throughput_offered_pct'])
receipt=dict(checks_passed=True,reproduced_runs=9,pilot_runs=9,
    checks='XY/TOPSIS reproduce audit baseline exactly; DyAD reproduces independent peak-VC variant; split counts reconcile; low-load delivery within 15% of nominal demand.')
(ROOT/'results/fair_reproduction/validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
