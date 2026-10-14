"""Publication-style figures from the same CSV schema consumed by MATLAB."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import t

METRICS = [
    ("latency_p50_cycles","p50 packet latency (cycles)"),
    ("latency_p90_cycles","p90 packet latency (cycles)"),
    ("latency_p99_cycles","99th-percentile latency (cycles)"),
    ("throughput_flits_per_node_cycle","Delivered throughput (flits/node/cycle)"),
    ("congested_port_time_pct","Congested port-time (%)"),
    ("link_utilization_pct","Mean link utilization (%)"),
    ("throughput_offered_pct","Delivered / offered traffic (%)"),
    ("wall_seconds","Simulator wall time (s)"),
]
COLORS = {"xy":"#0072B2","dyad":"#D55E00","topsis":"#009E73"}
STYLES = {"xy":"-","dyad":"--","topsis":"-."}

def main():
    p=argparse.ArgumentParser(); p.add_argument("result_dir",type=Path); args=p.parse_args()
    data=list(csv.DictReader((args.result_dir/"metrics.csv").open()))
    data=[r for r in data if r["status"]=="ok"]
    out=args.result_dir/"figures"; out.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.spines.top":False,
                         "axes.spines.right":False,"axes.labelsize":9,"axes.titlesize":11,
                         "figure.dpi":140,"savefig.dpi":300,"pdf.fonttype":42,"ps.fonttype":42})
    summaries=[]
    for k in sorted({int(r["mesh_k"]) for r in data}):
        for traffic in sorted({r["traffic"] for r in data}):
            group=[r for r in data if int(r["mesh_k"])==k and r["traffic"]==traffic]
            if not group: continue
            for sim in sorted({r["simulator"] for r in group}):
                fig,axes=plt.subplots(2,4,figsize=(15.6,7.4),layout="constrained")
                for ax,(metric,label) in zip(axes.flat,METRICS):
                    for alg in COLORS:
                        rows=[r for r in group if r["simulator"]==sim and r["algorithm"]==alg]
                        loads=sorted({float(r["offered_flits_per_node_cycle"]) for r in rows})
                        means=[]; errors=[]
                        for load in loads:
                            vals=np.array([float(r[metric]) for r in rows if float(r["offered_flits_per_node_cycle"])==load and r[metric]])
                            mean=float(vals.mean()); n=len(vals)
                            ci=float(t.ppf(.975,n-1)*vals.std(ddof=1)/np.sqrt(n)) if n>1 else 0
                            means.append(mean); errors.append(ci)
                            summaries.append(dict(simulator=sim,algorithm=alg,mesh_k=k,traffic=traffic,
                                                  load=load,metric=metric,n=n,mean=mean,ci95_halfwidth=ci))
                        ax.plot(loads,means,color=COLORS[alg],linestyle=STYLES[alg],
                                linewidth=2,label=alg.upper())
                        ax.fill_between(loads,np.array(means)-errors,np.array(means)+errors,
                                        color=COLORS[alg],alpha=.12,linewidth=0)
                    ax.set(xlabel="Offered load (flits/node/cycle)",ylabel=label)
                    ax.grid(alpha=.18); ax.set_axisbelow(True)
                    if metric.startswith("latency_"): ax.set_yscale("log")
                    else: ax.set_ylim(bottom=0)
                axes[0,0].legend(frameon=False,fontsize=8)
                model="flit-level NoC model" if sim=="booksim" else "packet-level store-and-forward approximation"
                fig.suptitle(f"{sim.upper()}  |  {k} × {k} mesh  |  {traffic}\n{model}; mean ± 95% t-interval across seeds",fontsize=14)
                for ext in ["png","pdf","svg"]: fig.savefig(out/f"{sim}_k{k}_{traffic}.{ext}")
                plt.close(fig)
    with (args.result_dir/"summary.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(summaries[0])); writer.writeheader(); writer.writerows(summaries)
    (args.result_dir/"summary.json").write_text(json.dumps(summaries,indent=2)+"\n")
    print(f"Wrote {len(list(out.glob('*.png')))} figure sets to {out}")

if __name__=="__main__": main()
