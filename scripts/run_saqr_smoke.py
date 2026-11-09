"""Smoke + stress test of the SAQR-build routes on frozen 4x4/8x8 transpose and
uniform traces (plumbing only; not tuning or evaluation evidence). UFA is the
unsafe control: a watchdog abort counts as an observed deadlock, not a failure."""
import json, subprocess, sys
from chr_common import ROOT, SAQR_STUDY, SAQR_BINARY, run
ROUTES=['xy','saqr','saqr_local','saqr_nogate','duato','westfirst','ufa']
CASES=[('k4_transpose_l7_s1',4),('k8_uniform_l8_s1',8),('k8_transpose_l8_s1',8)]
for name,k in CASES:
    demand=ROOT/'results/qos_comparison/cases'/name/'demand.txt'
    for alg in ROUTES:
        d=SAQR_STUDY/'smoke'/name/alg
        try:
            r=run(d,demand,k,alg,1,'weighted',binary=SAQR_BINARY)
        except subprocess.CalledProcessError:
            log=(d/'run.log').read_text()[-300:]
            print(f'{name:20s} {alg:12s} ABORTED:', 'watchdog (deadlock suspected)' if 'UFA_DEADLOCK' in log else log.strip().splitlines()[-1]); continue
        q=r['qos']['classes']; s=r['saqr']
        thr=sum(c['ejected_flits'] for c in q)/(20000*k*k)
        extra=''
        if s and s.get('classes'):
            c=s['classes']; routed=sum(x['routed'] for x in c) or 1
            extra=f"switched {100*sum(x['switched'] for x in c)/routed:5.1f}%  gated {100*sum(x['gated'] for x in c)/routed:5.1f}%  inv_checks {sum(x['invariant_checks'] for x in c)}"
        print(f"{name:20s} {alg:12s} integrity {r['qos']['integrity_errors']}  crit_p99 {q[0]['latency_p99_cycles']:6}  be_p99 {q[1]['latency_p99_cycles']:6}  thr {thr:.4f}  {extra}",flush=True)
