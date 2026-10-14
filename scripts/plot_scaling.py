"""Line-only size-scaling figures and concise evidence tables."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import t
from plot_results import COLORS, STYLES

METRICS=[("latency_p50_cycles","p50 latency (cycles)"),("latency_p90_cycles","p90 latency (cycles)"),
         ("latency_p99_cycles","p99 latency (cycles)"),
         ("throughput_flits_per_node_cycle","Throughput (flits/node/cycle)"),
         ("congested_port_time_pct","Congested port-time (%)")]

def main():
    p=argparse.ArgumentParser(); p.add_argument("result_dir",type=Path); a=p.parse_args()
    rows=list(csv.DictReader((a.result_dir/"metrics.csv").open()))
    good=[r for r in rows if r["status"]=="ok"]
    out=a.result_dir/"figures"; out.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.spines.top":False,
                         "axes.spines.right":False,"pdf.fonttype":42,"savefig.dpi":300})
    summary=[]
    for traffic in sorted({r["traffic"] for r in good}):
        for load in sorted({float(r["offered_flits_per_node_cycle"]) for r in good}):
            group=[r for r in good if r["traffic"]==traffic and float(r["offered_flits_per_node_cycle"])==load]
            fig,axes=plt.subplots(2,5,figsize=(18,7.7),layout="constrained")
            for ri,sim in enumerate(["booksim","ns2"]):
                for ax,(metric,label) in zip(axes[ri],METRICS):
                    for algorithm in COLORS:
                        subset=[r for r in group if r["simulator"]==sim and r["algorithm"]==algorithm]
                        sizes=sorted({int(r["mesh_k"]) for r in subset})
                        means=[]; ci=[]
                        for size in sizes:
                            vals=np.array([float(r[metric]) for r in subset if int(r["mesh_k"])==size])
                            mean=float(vals.mean()); n=len(vals)
                            half=float(t.ppf(.975,n-1)*vals.std(ddof=1)/np.sqrt(n)) if n>1 else 0
                            means.append(mean); ci.append(half)
                            summary.append(dict(simulator=sim,algorithm=algorithm,traffic=traffic,offered_load=load,
                                                mesh_k=size,n=n,metric=metric,mean=mean,ci95_halfwidth=half))
                        ax.plot(sizes,means,color=COLORS[algorithm],linestyle=STYLES[algorithm],linewidth=2,label=algorithm.upper())
                        lower=np.array(means)-ci
                        if metric.startswith("latency"): lower=np.maximum(lower,.1)
                        ax.fill_between(sizes,lower,np.array(means)+ci,color=COLORS[algorithm],alpha=.12,linewidth=0)
                    ax.set_xscale("log",base=2); ax.set_xticks([4,8,16,32],["4×4","8×8","16×16","32×32"])
                    ax.set(xlabel="Mesh size",ylabel=label); ax.grid(alpha=.18)
                    if metric.startswith("latency"): ax.set_yscale("log")
                    else: ax.set_ylim(bottom=0)
                axes[ri,0].set_title(sim.upper()+ (" — flit-level" if sim=="booksim" else " — packet approximation"),loc="left",fontsize=11)
                axes[ri,0].legend(frameon=False,fontsize=8)
            fig.suptitle(f"Scaling from 16 to 1,024 routers | {traffic} | offered load {load:g} flits/node/cycle\n"
                         "Lines: mean across seeds; shading: 95% t-interval. Latencies condition on completed packets.",fontsize=14)
            for ext in ["png","pdf","svg"]: fig.savefig(out/f"scaling_{traffic}_load{load}.{ext}")
            plt.close(fig)
    with (a.result_dir/"scaling_summary.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=summary[0]); w.writeheader(); w.writerows(summary)
    report=["# Measured size-scaling pilot\n",f"Successful simulator runs: {len(good)} / {len(rows)}.\n",
            "Latency columns are means of each run's nearest-rank percentiles. They exclude unfinished packets; assess throughput and congestion alongside latency.\n",
            "| Engine | Traffic | Load | Mesh | Algorithm | p50 | p90 | p99 | Throughput | Congested % |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    keys=sorted({(r["simulator"],r["traffic"],float(r["offered_flits_per_node_cycle"]),int(r["mesh_k"]),r["algorithm"]) for r in good})
    for sim,traffic,load,k,alg in keys:
        values=[next(s["mean"] for s in summary if (s["simulator"],s["traffic"],s["offered_load"],s["mesh_k"],s["algorithm"],s["metric"])==(sim,traffic,load,k,alg,m)) for m,_ in METRICS]
        report.append(f"| {sim} | {traffic} | {load:g} | {k}×{k} | {alg} | "+" | ".join(f"{v:.4g}" for v in values)+" |")
    report.extend(["", "These finite-window simulations are not a SOTA benchmark or numerical accuracy measurement. Equal routing-stage delays exclude hardware arithmetic cost. Concurrent-process wall times are diagnostic, not fair timing benchmarks. See docs/METHODOLOGY.md and each case's raw logs/configuration."])
    (a.result_dir/"RESULTS.md").write_text("\n".join(report)+"\n")
    rankings=["# Which algorithm performs better as the mesh grows?\n",
              "Descriptive seed means only. A lower completed-packet p99 does not establish a better system if throughput or delivery deteriorates. Close/overlapping intervals are not significant wins.\n",
              "| Simulator | Traffic | Load | Mesh | Lowest measured p99 | Highest measured throughput | Offered traffic served: XY / DyAD / TOPSIS |",
              "|---|---|---:|---:|---|---|---|"]
    groups=sorted({(r["simulator"],r["traffic"],float(r["offered_flits_per_node_cycle"]),int(r["mesh_k"])) for r in good})
    for sim,traffic,load,k in groups:
        stats={}
        for alg in COLORS:
            r=[r for r in good if (r["simulator"],r["traffic"],float(r["offered_flits_per_node_cycle"]),int(r["mesh_k"]),r["algorithm"])==(sim,traffic,load,k,alg)]
            if r:
                stats[alg]=(np.mean([float(x["latency_p99_cycles"]) for x in r]),
                            np.mean([float(x["throughput_flits_per_node_cycle"]) for x in r]),
                            np.mean([float(x["throughput_offered_pct"]) for x in r]))
        if len(stats)!=3: continue
        low=min(v[0] for v in stats.values()); high=max(v[1] for v in stats.values())
        low_names=" / ".join(alg.upper() for alg,v in stats.items() if np.isclose(v[0],low))
        high_names=" / ".join(alg.upper() for alg,v in stats.items() if np.isclose(v[1],high))
        service=" / ".join(f"{stats[alg][2]:.1f}%" for alg in COLORS)
        rankings.append(f"| {sim} | {traffic} | {load:g} | {k}x{k} | {low_names} ({low:.1f} cycles) | {high_names} ({high:.4f} flits/node/cycle) | {service} |")
    rankings.extend(["", "At fixed per-node injection, offered aggregate traffic grows with k², whereas mesh bisection capacity grows with k. Routing cannot remove this physical limit. Hotspot traffic additionally tests a single destination's capacity. The NS-2 model omits that shared ejection constraint, so cross-engine curve ordering is not an accuracy measurement."])
    (a.result_dir/"RANKINGS.md").write_text("\n".join(rankings)+"\n")
    print(f"Wrote scaling line figures and report to {a.result_dir}")

if __name__=="__main__": main()
