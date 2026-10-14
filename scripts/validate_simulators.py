"""Independent serialization checks and custom-XY vs upstream-XY regression."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_experiments import ROOT, invoke, ns_metrics

def main():
    out=ROOT/"results/validation"; out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for flits in [1,5,9]:
        for dst in [1,2,7,15]:
            hops=dst%4+dst//4
            arrivals=out/f"isolated_p{flits}_d{dst}.tcl"
            arrivals.write_text(f'$ns at 0.000001 "generate 0 {dst}"\n')
            prefix=out/f"isolated_p{flits}_d{dst}"
            command=["ns",str(ROOT/"simulators/ns2/mesh.tcl"),"xy","4",str(arrivals),str(prefix),"0","1000",str(flits)]
            _,status=invoke(command,Path(str(prefix)+".log"))
            assert status=="ok", prefix
            result=ns_metrics(prefix,0,1000,flits)
            expected=hops*(flits+1)
            measured=result["latency_mean_cycles"]
            assert result["delivered_packets"]==1
            assert abs(measured-expected)<1e-7,(expected,measured)
            rows.append(dict(packet_flits=flits,hops=hops,expected_cycles=expected,measured_cycles=measured))
    with (out/"serialization.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    # Identical workload and microarchitecture: our XY must match BookSim DOR.
    sample=ROOT/"results/smoke/raw/booksim_xy_k4_uniform_l0.1_s1.cfg"
    base=sample.read_text()
    results=[]
    for route in ["noc_xy","dim_order"]:
        cfg=out/f"{route}.cfg"; cfg.write_text(base.replace("routing_function = noc_xy;",f"routing_function = {route};"))
        metrics=out/f"{route}.json"
        env=dict(os.environ,NOC_WARMUP="100",NOC_MEASURE="500",NOC_METRICS=str(metrics))
        _,status=invoke([str(ROOT/".deps/booksim2/src/booksim"),str(cfg)],out/f"{route}.log",env)
        assert status=="ok"
        results.append(json.loads(metrics.read_text()))
    assert results[0]==results[1], "Custom XY differs from upstream dimension-order routing"
    (out/"validation.json").write_text(json.dumps(dict(ns2_serialization_cases=len(rows),
        max_abs_error=max(abs(r["expected_cycles"]-r["measured_cycles"]) for r in rows),
        booksim_xy_matches_upstream=True),indent=2)+"\n")
    print("PASS: 12 NS-2 analytical serialization cases; BookSim XY matches upstream DOR exactly")

if __name__=="__main__": main()
