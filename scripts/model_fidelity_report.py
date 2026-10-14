"""Plot a specific missing NoC constraint, without inventing an accuracy percentage."""
import argparse
import csv
from pathlib import Path
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser(); p.add_argument("result_dir",type=Path); args=p.parse_args()
    rows=list(csv.DictReader((args.result_dir/"metrics.csv").open()))
    rows=[r for r in rows if r["status"]=="ok" and r["traffic"]=="hotspot" and r["algorithm"]=="xy"]
    out=args.result_dir/"figures"; out.mkdir(exist_ok=True)
    sizes=sorted({int(r["mesh_k"]) for r in rows})
    fig,axes=plt.subplots(1,len(sizes),figsize=(6.5*len(sizes),4.6),squeeze=False,layout="constrained")
    summary=[]
    for ax,k in zip(axes[0],sizes):
        for sim,color,style in [("booksim","#0072B2","-"),("ns2","#D55E00","--")]:
            group=[r for r in rows if int(r["mesh_k"])==k and r["simulator"]==sim]
            loads=sorted({float(r["offered_flits_per_node_cycle"]) for r in group})
            means=[]
            for load in loads:
                vals=[float(r["throughput_flits_per_node_cycle"])*k*k for r in group if float(r["offered_flits_per_node_cycle"])==load]
                means.append(statistics.mean(vals))
                summary.append(dict(simulator=sim,mesh_k=k,offered_load=load,aggregate_throughput=means[-1]))
            ax.plot(loads,means,label=sim.upper(),color=color,linestyle=style,linewidth=2.2)
        ax.axhline(1,color="#444444",linestyle=":",label="One-flit/cycle ejection capacity")
        ax.set(xlabel="Offered load (flits/node/cycle)",ylabel="Aggregate delivered traffic (flits/cycle)",
               title=f"{k} × {k}: all traffic to one destination",ylim=(0,None))
        ax.spines[["top","right"]].set_visible(False); ax.grid(alpha=.18); ax.legend(frameon=False,fontsize=9)
    fig.suptitle("A missing destination bottleneck changes the result\nNS-2 model has no shared ejection server; disagreement is not an accuracy percentage",fontsize=13)
    for ext in ["png","pdf","svg"]: fig.savefig(out/f"model_fidelity.{ext}",dpi=300)
    plt.close(fig)
    with (args.result_dir/"hotspot_capacity.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=summary[0]); w.writeheader(); w.writerows(summary)
    for r in rows:
        if r["simulator"]=="booksim":
            capacity=1+float(r["packet_flits"])/float(r["measurement_cycles"])
            assert float(r["throughput_flits_per_node_cycle"])*int(r["nodes"])<=capacity+1e-9
    print("PASS: BookSim hotspot throughput respects shared ejection capacity")

if __name__=="__main__": main()
