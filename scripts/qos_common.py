"""Shared demand generation and configuration for reproducible QoS experiments."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BINARY=ROOT/'.deps/booksim2_qos/src/booksim'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def trace(path,k,load,seed,traffic,warm=5000,cycles=20000,classes=2):
    rng=np.random.default_rng(seed)
    n=k*k
    states=rng.integers(0,2,n).astype(bool)
    hotspot={'hotspot_corner':0,'hotspot_edge':k//2,'hotspot_center':(k//2)*k+k//2}
    count=0
    with Path(path).open('w') as out:
        for t in range(warm+cycles):
            probability=load/5
            if traffic=='bursty':
                states^=rng.random(n)<.02
                probability=states*2*load/5
            sources=np.flatnonzero(rng.random(n)<probability)
            dest=rng.integers(0,n,len(sources))
            if traffic=='transpose': dest=(sources%k)*k+sources//k
            elif traffic in hotspot:
                dest=np.where(rng.random(len(sources))<.2,hotspot[traffic],dest)
            cls=np.where(rng.random(len(sources))<.25,0,1) if classes==2 else np.zeros(len(sources),dtype=int)
            out.writelines(f'{t} {s} {d} {c}\n' for s,d,c in zip(sources,dest,cls))
            count+=len(sources)
    return count

def config(k,algorithm,seed,mode,classes=2,vcs=4,depth=8):
    return f'''topology = mesh; k = {k}; n = 2;
routing_function = noc_{algorithm}; classes = {classes};
num_vcs = {vcs}; vc_buf_size = {depth}; router = iq;
vc_allocator = separable_output_first; sw_allocator = separable_output_first;
arb_type = {'qos_weighted' if mode=='weighted' else 'round_robin'};
alloc_iters = 1; routing_delay = 1; vc_alloc_delay = 1; sw_alloc_delay = 1;
st_prepare_delay = 0; st_final_delay = 1; credit_delay = 1;
speculative = 0; wait_for_tail_credit = 1; hold_switch_for_packet = 0;
traffic = uniform; packet_size = 5; injection_rate = 0.0;
injection_process = bernoulli; seed = {seed}; priority = class;
sim_type = throughput; sim_count = 1;
'''

def run(directory,demand,k,algorithm='xy',seed=1,mode='weighted',warm=5000,cycles=20000,classes=2,vcs=4,depth=8,events=False,timeout=3600):
    directory=Path(directory).resolve(); directory.mkdir(parents=True,exist_ok=True)
    cfg=directory/'config.cfg'; cfg.write_text(config(k,algorithm,seed,mode,classes,vcs,depth))
    env=dict(os.environ,NOC_TRACE=str(Path(demand).resolve()),NOC_WARMUP=str(warm),NOC_MEASURE=str(cycles),
             NOC_SKIP_DRAIN='1',NOC_QOS_MODE=mode,NOC_METRICS=str(directory/'aggregate.json'),NOC_QOS_METRICS=str(directory/'classes.json'))
    if events: env['NOC_QOS_EVENTS']=str(directory/'events.csv')
    start=time.perf_counter()
    with (directory/'run.log').open('w') as out:
        subprocess.run([str(BINARY),str(cfg)],stdout=out,stderr=subprocess.STDOUT,env=env,check=True,timeout=timeout)
    result=dict(k=k,algorithm=algorithm,seed=seed,mode=mode,warm=warm,cycles=cycles,classes=classes,vcs=vcs,depth=depth,
                binary_sha256=sha(BINARY),trace_sha256=sha(demand),config_sha256=sha(cfg),wall_seconds=time.perf_counter()-start,
                aggregate=json.loads((directory/'aggregate.json').read_text()),qos=json.loads((directory/'classes.json').read_text()))
    (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
