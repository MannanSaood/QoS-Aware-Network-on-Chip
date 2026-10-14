"""Predeclared lower-load, longer-window BookSim study; never reuse the old grid."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import itertools
import json
import subprocess
import sys
from run_experiments import ROOT, write_rows

SIZES=[4,8,16,32]
TRAFFIC=['uniform','transpose','bursty','hotspot_corner','hotspot_edge','hotspot_center']
SEEDS=[1,2,3]
WARMUP=5000
CYCLES=20000
OUT=ROOT/'results/fair_comparison'

def loads(k,traffic):
    if traffic.startswith('hotspot_'):
        reference=1/(.2*k*k+.8)
        factors=[.1,.25,.5,.7,.85,1,1.15,1.5,2]
    else:
        reference=4/k
        factors=[.02,.05,.1,.2,.3,.4,.6,.8,1]
    return [float(format(reference*f,'.12g')) for f in factors]

def protocol():
    return dict(version='peak_vc_dyad_v1',sizes=SIZES,traffic=TRAFFIC,seeds=SEEDS,
        warmup_cycles=WARMUP,measurement_cycles=CYCLES,packet_flits=5,
        num_vcs=4,vc_buf_size=8,routing_delay=1,dyad_threshold=.6,topsis_weights=[.7,.3],
        load_grid={f'k{k}_{t}':loads(k,t) for k in SIZES for t in TRAFFIC},
        expected_runs=1944,
        randomization='Native BookSim traffic, matched seed IDs; not identical packet traces.',
        reference_note='4/k is a uniform bisection upper-bound scale, not a saturation prediction. Hotspot reference is shared-ejection necessary bound 1/(0.2*k*k+0.8).',
        latency_note='Finite-window completed-packet latency; no steady-state or equivalence claim.',
        drift_rule='Diagnostic flag if second-half p99 > 1.25*first-half p99 or second-half throughput differs by >10% from first half; low counts (<1000 delivered) separately flagged.')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--pilot',action='store_true'); a=p.parse_args()
    output=ROOT/'results/fair_pilot' if a.pilot else OUT
    output.mkdir(parents=True,exist_ok=True)
    binary=ROOT/'.deps/booksim2/src/booksim'
    spec=protocol(); spec['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
    files=list((ROOT/'algorithms').rglob('*.hpp'))+list((ROOT/'simulators/booksim').glob('*.*'))
    files += [ROOT/'scripts/run_experiments.py',ROOT/'scripts/run_fair_grid.py',ROOT/'scripts/setup.py']
    spec['sources_sha256']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    path=output/'protocol.json'
    if path.exists(): assert json.loads(path.read_text())==spec,'Protocol/source changed: use a separate study directory'
    else: path.write_text(json.dumps(spec,indent=2)+'\n')
    cases=[(k,t,l,s) for k,t,s in itertools.product(SIZES,TRAFFIC,SEEDS) for l in loads(k,t)]
    if a.pilot: cases=[(4,'uniform',.02,1),(8,'transpose',.05,1),(32,'hotspot_center',loads(32,'hotspot_center')[0],1)]
    rows=[]; failed=[]
    def work(case):
        k,t,l,s=case; dest=output/'cases'/f'k{k}_{t}_l{l}_s{s}'; dest.mkdir(parents=True,exist_ok=True)
        command=[sys.executable,str(ROOT/'scripts/run_experiments.py'),'--simulators','booksim',
            '--sizes',str(k),'--loads',str(l),'--traffic',t,'--seeds',str(s),
            '--warmup',str(WARMUP),'--cycles',str(CYCLES),'--output',str(dest),'--resume','--timeout-seconds','3600']
        with (dest/'runner.log').open('w') as f: result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
        result_path=dest/'metrics.json'
        return case,result.returncode,json.loads(result_path.read_text()) if result_path.exists() else []
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for future in as_completed([pool.submit(work,c) for c in cases]):
            case,code,new=future.result(); rows.extend(new)
            if code: failed.append(case)
            write_rows(output,rows)
            state=dict(expected_runs=3*len(cases),actual_rows=len(rows),failed_cases=failed,complete=len(rows)==3*len(cases) and not failed)
            (output/'progress.json').write_text(json.dumps(state,indent=2)+'\n')
            print(f'{len(rows)}/{3*len(cases)} runs; latest {case}; failures {len(failed)}',flush=True)
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==spec['binary_sha256'],'Binary changed during study'
    assert not failed and len(rows)==3*len(cases), 'Incomplete study; inspect raw logs and resume'
    (output/'manifest.json').write_text(json.dumps(dict(**spec,actual_rows=len(rows),complete=True),indent=2)+'\n')

if __name__=='__main__': main()
