"""Run real BookSim and NS-2 processes, preserve logs, emit a common CSV/JSON schema."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import shutil
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["simulator", "algorithm", "mesh_k", "nodes", "traffic", "offered_flits_per_node_cycle", "execution_profile",
          "seed", "packet_flits", "warmup_cycles", "measurement_cycles", "status",
          "delivered_packets", "latency_mean_cycles", "latency_p50_cycles", "latency_p90_cycles", "latency_p95_cycles", "latency_p99_cycles",
          "throughput_flits_per_node_cycle", "throughput_offered_pct", "buffer_occupancy_pct",
          "congested_port_time_pct", "link_utilization_pct", "peak_link_utilization_pct", "mean_hops",
          "wall_seconds", "drops", "generated_packets", "cohort_delivery_pct", "physical_directed_links",
          "binary_sha256", "first_half_delivered_packets", "second_half_delivered_packets",
          "first_half_p99_cycles", "second_half_p99_cycles"]

def invoke(command, log, env=None, timeout=900):
    start = time.perf_counter()
    with log.open("w") as out:
        try:
            result = subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return time.perf_counter()-start, "timeout"
    return time.perf_counter()-start, "ok" if result.returncode == 0 else "failed"

def hotspot_node(k,traffic):
    return {'hotspot_corner':0,'hotspot_edge':k//2,'hotspot_center':(k//2)*k+k//2}[traffic]

def execution_profile(sim,traffic):
    if sim=='booksim' and (traffic=='bursty' or traffic.startswith('hotspot_')):
        return 'booksim_parameter_lists_v3'
    return 'manual_routes_percentiles_v2'

def booksim_traffic_config(k,traffic):
    # BookSim tokenize_str requires outer braces around a parameter list.
    # The two nested hotspot lists must stay intact as its two arguments.
    pattern=f'hotspot({(k//2)*k+k//2})' if traffic=='hotspot' else traffic
    injection='bernoulli'
    if traffic=='bursty':
        pattern='uniform'; injection='on_off({0.02,0.02,-1})'
    if traffic.startswith('hotspot_'):
        nodes=','.join(str(i) for i in range(k*k))
        weights=','.join(str(4+k*k if i==hotspot_node(k,traffic) else 4) for i in range(k*k))
        pattern='hotspot({{'+nodes+'},{'+weights+'}})'
    return pattern,injection

def destinations(rng, src, k, traffic):
    if traffic in ("uniform","bursty"):
        return rng.randrange(k*k)  # Includes self, matching upstream BookSim.
    if traffic == "transpose":
        return (src % k)*k + src//k
    if traffic == "hotspot":
        return (k//2)*k + k//2
    if traffic.startswith('hotspot_'):
        return hotspot_node(k,traffic) if rng.random()<.2 else rng.randrange(k*k)
    raise ValueError(traffic)

def arrivals(path, k, load, seed, traffic, warmup, cycles, flits):
    rng = random.Random(seed)
    states=[rng.randrange(2) for _ in range(k*k)] if traffic=='bursty' else None
    with path.open("w") as out:
        for cycle in range(warmup+cycles):
            for src in range(k*k):
                probability=load/flits
                if states is not None:
                    states[src]=int(rng.random()>=.02) if states[src] else int(rng.random()<.02)
                    probability=2*load/flits if states[src] else 0
                if rng.random() < probability:
                    dst = destinations(rng, src, k, traffic)
                    # A quarter-cycle offset avoids sample/generation ordering ambiguity.
                    out.write(f'$ns at {(cycle+.25)*1e-6:.12f} "generate {src} {dst}"\n')

def ns_metrics(prefix, warmup, cycles, flits):
    latency, hops = [], []
    for line in Path(str(prefix)+".events").read_text().splitlines():
        bits = line.split()
        if bits[0] == "D":
            latency.append(float(bits[2])); hops.append(float(bits[3]))
        if bits[0] == "SUMMARY":
            generated, delivered, cohort, occupancy, congested, samples, links = map(float, bits[1:])
    latency.sort()
    def percentile(p):
        return latency[max(0, math.ceil(p*len(latency))-1)] if latency else math.nan
    busy = {}; drops = 0
    start, stop = warmup*1e-6, (warmup+cycles)*1e-6
    trace_path = Path(str(prefix)+".tr")
    with trace_path.open() as trace:
        for line in trace:
            bits = line.split()
            if len(bits)<6:
                continue
            event, t, src, dst = bits[:4]; t = float(t)
            if event == "d" and start <= t < stop:
                drops += 1
            if event == "-":
                duration = int(bits[5])*8/32e6
                overlap = max(0, min(stop, t+duration)-max(start, t))
                busy[src,dst] = busy.get((src,dst), 0) + overlap
    # Keep actual NS-2 event traces as compressed provenance, never synthesize results.
    with trace_path.open("rb") as src, gzip.open(str(trace_path)+".gz", "wb") as dst:
        import shutil
        shutil.copyfileobj(src, dst)
    trace_path.unlink()
    return dict(delivered_packets=int(delivered), latency_mean_cycles=statistics.mean(latency) if latency else math.nan,
                latency_p50_cycles=percentile(.50), latency_p90_cycles=percentile(.90),
                latency_p95_cycles=percentile(.95), latency_p99_cycles=percentile(.99),
                buffer_occupancy_pct=100*occupancy/(samples*links),
                congested_port_time_pct=100*congested/(samples*links),
                link_utilization_pct=100*sum(busy.values())/((stop-start)*links),
                peak_link_utilization_pct=100*max(busy.values(),default=0)/(stop-start),
                mean_hops=statistics.mean(hops) if hops else math.nan, drops=drops,
                generated_packets=int(generated), cohort_delivery_pct=100*cohort/generated if generated else math.nan,
                physical_directed_links=int(links), measurement_cycles=cycles)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--simulators", nargs="+", choices=["booksim", "ns2"], default=["booksim", "ns2"])
    p.add_argument("--algorithms", nargs="+", choices=["xy", "dyad", "topsis"], default=["xy", "dyad", "topsis"])
    p.add_argument("--sizes", nargs="+", type=int, default=[4,8])
    p.add_argument("--loads", nargs="+", type=float, default=[.02,.1,.2,.35,.5,.7])
    p.add_argument("--seeds", nargs="+", type=int, default=[1,2,3])
    p.add_argument("--traffic", nargs="+", choices=["uniform","transpose","hotspot","bursty","hotspot_corner","hotspot_edge","hotspot_center"], default=["uniform","transpose","hotspot"])
    p.add_argument("--warmup", type=int, default=1000)
    p.add_argument("--cycles", type=int, default=5000)
    p.add_argument("--packet-flits", type=int, default=5)
    p.add_argument("--output", type=Path, default=ROOT/"results/baseline")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--timeout-seconds",type=int,default=900,help="Wall-clock limit per simulator process; does not change simulated cycles")
    a = p.parse_args()
    if min(a.sizes)<2 or min(a.loads)<=0 or max(a.loads)>1 or a.cycles<=0 or a.warmup<0 or a.packet_flits<1 or a.timeout_seconds<=0:
        p.error("need sizes>=2, 0<load<=1, cycles>0, warmup>=0, packet-flits>=1")
    if "transpose" in a.traffic and any(k & (k-1) for k in a.sizes) and "booksim" in a.simulators:
        p.error("upstream BookSim transpose requires power-of-two mesh side; use uniform/hotspot for 3x3")
    a.output = a.output.resolve(); raw = a.output/"raw"; raw.mkdir(parents=True, exist_ok=True)
    rows = []
    binaries={'booksim': ROOT/'.deps/booksim2/src/booksim', 'ns2': ROOT/'build/nocroute.so'}
    binary_hashes={sim:hashlib.sha256(binaries[sim].read_bytes()).hexdigest() for sim in a.simulators}
    for k in a.sizes:
        for traffic in a.traffic:
            for load in a.loads:
                for seed in a.seeds:
                    arrivals_path = raw/f"arrivals_k{k}_{traffic}_{load}_{seed}.tcl"
                    if "ns2" in a.simulators:
                        arrivals(arrivals_path,k,load,seed,traffic,a.warmup,a.cycles,a.packet_flits)
                    for sim in a.simulators:
                        for algorithm in a.algorithms:
                            stem=f"{sim}_{algorithm}_k{k}_{traffic}_l{load}_s{seed}"
                            prefix=raw/stem; result_path=raw/(stem+".json")
                            row=dict(simulator=sim,algorithm=algorithm,mesh_k=k,nodes=k*k,traffic=traffic,
                                     offered_flits_per_node_cycle=load,seed=seed,packet_flits=a.packet_flits,
                                     warmup_cycles=a.warmup,measurement_cycles=a.cycles,execution_profile=execution_profile(sim,traffic),
                                     binary_sha256=binary_hashes[sim])
                            if a.resume and result_path.exists():
                                cached=json.loads(result_path.read_text())
                                if all(cached.get(key)==value for key,value in row.items()) and cached["status"]=="ok":
                                    rows.append(cached); continue
                                if cached.get('status')!='ok':
                                    attempts=raw/'failed_attempts'; attempts.mkdir(exist_ok=True)
                                    for suffix in ['.json','.log']:
                                        evidence=raw/(stem+suffix)
                                        if evidence.exists(): shutil.copyfile(evidence,attempts/evidence.name)
                                if cached.get('execution_profile')!=row['execution_profile']:
                                    archive=ROOT/'results/development/invalid_parameter_format'/a.output.relative_to(ROOT/'results')/'raw'
                                    archive.mkdir(parents=True,exist_ok=True)
                                    for evidence in raw.glob(stem+'.*'):
                                        shutil.copyfile(evidence,archive/evidence.name)
                            if sim=="booksim":
                                config=raw/(stem+".cfg")
                                pattern,injection=booksim_traffic_config(k,traffic)
                                config.write_text(f'''topology = mesh;
k = {k}; n = 2;
routing_function = noc_{algorithm};
num_vcs = 4; vc_buf_size = 8;
router = iq;
vc_allocator = islip; sw_allocator = islip; alloc_iters = 1;
routing_delay = 1; vc_alloc_delay = 1; sw_alloc_delay = 1;
st_prepare_delay = 0; st_final_delay = 1; credit_delay = 1;
speculative = 0; wait_for_tail_credit = 1;
traffic = {pattern};
packet_size = {a.packet_flits}; injection_rate = {load/a.packet_flits};
injection_process = {injection}; seed = {seed};
sim_type = throughput; sim_count = 1;
''')
                                metrics=raw/(stem+".metrics.json")
                                env=dict(os.environ,NOC_WARMUP=str(a.warmup),NOC_MEASURE=str(a.cycles),NOC_METRICS=str(metrics),NOC_SKIP_DRAIN='1')
                                wall,status=invoke([str(ROOT/".deps/booksim2/src/booksim"),str(config)],raw/(stem+".log"),env,timeout=a.timeout_seconds)
                                if status=="ok":
                                    row.update(json.loads(metrics.read_text()))
                                    row["drops"]=0 # lossless credit flow control; source backlog is not packet loss
                            else:
                                # Avoid per-event writes through Windows/DrvFS. Copy compressed evidence back.
                                with tempfile.TemporaryDirectory(prefix="noc-ns2-") as scratch:
                                    scratch=Path(scratch); local_prefix=scratch/stem
                                    local_arrivals=scratch/"arrivals.tcl"; shutil.copyfile(arrivals_path,local_arrivals)
                                    command=["ns",str(ROOT/"simulators/ns2/mesh.tcl"),algorithm,str(k),str(local_arrivals),str(local_prefix),
                                             str(a.warmup),str(a.cycles),str(a.packet_flits)]
                                    wall,status=invoke(command,scratch/(stem+".log"),timeout=a.timeout_seconds)
                                    if status=="ok": row.update(ns_metrics(local_prefix,a.warmup,a.cycles,a.packet_flits))
                                    for evidence in scratch.glob(stem+".*"):
                                        shutil.copyfile(evidence,raw/evidence.name)
                            row.update(wall_seconds=wall,status=status)
                            if status=="ok":
                                throughput=row["delivered_packets"]*a.packet_flits/(a.cycles*k*k)
                                row.update(throughput_flits_per_node_cycle=throughput,throughput_offered_pct=100*throughput/load)
                                if row["physical_directed_links"]!=4*k*(k-1):
                                    raise RuntimeError(f"incorrect physical link count: {stem}")
                                for metric in ["buffer_occupancy_pct","link_utilization_pct","peak_link_utilization_pct"]:
                                    if not 0<=row[metric]<=100.001: raise RuntimeError(f"invalid {metric}: {row}")
                            result_path.write_text(json.dumps(row,indent=2)+"\n")
                            rows.append(row)
                            print(f"{stem}: {status}, {wall:.2f}s",flush=True)
                            write_rows(a.output,rows)
    write_rows(a.output,rows)
    sources = sorted(list((ROOT/"algorithms").rglob("*.hpp"))+list((ROOT/"simulators").rglob("*.*"))+list((ROOT/"scripts").glob("*.py")))
    manifest=dict(arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
                  platform=platform.platform(),python=platform.python_version(),
                  booksim_revision=subprocess.check_output(["git","-C",str(ROOT/".deps/booksim2"),"rev-parse","HEAD"],text=True).strip(),
                  source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},
                  rows=len(rows),failed=sum(r["status"]!="ok" for r in rows))
    manifest['binary_sha256']=binary_hashes
    (a.output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    if manifest["failed"]: raise SystemExit(f'{manifest["failed"]} simulations failed; see raw logs')

def write_rows(output,rows):
    with (output/"metrics.csv").open("w",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS,extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    (output/"metrics.json").write_text(json.dumps(rows,indent=2)+"\n")

if __name__=="__main__": main()
