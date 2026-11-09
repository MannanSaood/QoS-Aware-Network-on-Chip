"""Smoke test: every CHR-study route runs, passes integrity checks and emits counters.
Uses one frozen 4x4 transpose trace for plumbing only; not tuning or evaluation evidence."""
import json
from chr_common import ROOT, STUDY, run
demand=ROOT/'results/qos_comparison/cases/k4_transpose_l7_s1/demand.txt'
for alg in ['oefixed','chr_cls','chr_hyst','chr_nofv','chr']:
    r=run(STUDY/'smoke'/alg,demand,4,alg,1,'weighted')
    c=r['qos']['classes']; h=r['chr']['classes']
    print(alg,'integrity',r['qos']['integrity_errors'],'crit_p99',c[0]['latency_p99_cycles'],
          'thr',round(r['aggregate']['link_utilization_pct'],2),
          'dual',[x['dual_candidate_decisions'] for x in h],'pressured',[x['pressured_decisions'] for x in h],
          'switched',[x['switched_decisions'] for x in h],'h_on%',[round(100*x['hysteresis_on_samples']/max(1,x['hysteresis_samples']),1) for x in h],
          'h_trans',[x['hysteresis_transitions'] for x in h],flush=True)
