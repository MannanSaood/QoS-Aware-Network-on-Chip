"""Slide-sized versions of the final SAQR-C figures, styled for the project deck
(Times New Roman, navy panel titles, legend built in, no figure title: the slide carries it).

usage: python scripts/plot_saqr_slides.py OUT_DIR
Writes g6_k{4,8,16,32}_{p99_latency,throughput,congestion}.png (15 panels each, G6 seeds 401-405)
and nt_k8_{...}.png (3 PARSEC panels, Netrace). Data: the frozen G6 / Netrace receipts, the
nine comparators and SAQR-C only. Means over seeds, linear axes from zero, no markers.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plot_saqr_study as ps  # noqa: E402

NAVY = '#002060'
GREY = '#516070'
ORDER = ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint', 'o1turn', 'saqr_c']
METRICS = [('crit_p99', 'p99 latency (cycles)', 'p99_latency'),
           ('throughput', 'flits / node / cycle', 'throughput'),
           ('congested', 'congested port-time (%)', 'congestion')]
SHORT = dict(ps.TITLE, hotspot_corner='Hotspot: corner', hotspot_edge='Hotspot: edge', hotspot_center='Hotspot: center',
             multiflow='Multi-flow (4 dests)', mixed='Mixed (50 % transpose)')


def draw(stage, out):
    proto, routes, acc = ps.load(stage)
    routes = [r for r in ORDER if r in routes]
    traffic = proto['traffic']
    plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.titlesize': 11, 'axes.titleweight': 'bold',
                         'axes.titlecolor': NAVY, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
                         'axes.edgecolor': '#8A95A3', 'savefig.dpi': 220})
    cols = 5 if len(traffic) > 4 else len(traffic)
    rows = -(-len(traffic) // cols)
    size = (12.7, 5.75) if rows == 3 else (12.7, 4.6)
    for k in proto['meshes']:
        for key, ylab, fname in METRICS:
            fig, axes = plt.subplots(rows, cols, figsize=size, squeeze=False)
            for ax, t in zip(axes.flat, traffic):
                for r in routes:
                    pts = sorted((ld, sum(m[key] for m in v) / len(v)) for (kk, tt, ld, rr), v in acc.items()
                                 if kk == k and tt == t and rr == r)
                    main = r == 'saqr_c'
                    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=ps.COLOR[r], label=ps.LABEL[r],
                            linewidth=2.4 if main else 1.0, linestyle='-' if main or r == 'xy' else '--', zorder=3 if main else 2)
                ax.set_title(SHORT.get(t, t), pad=3)
                ax.set_xlim(left=0); ax.set_ylim(bottom=0)
                ax.grid(alpha=.18); ax.set_axisbelow(True)
                ax.ticklabel_format(axis='y', style='sci', scilimits=(-3, 4), useMathText=True)
                ax.yaxis.get_offset_text().set_fontsize(7)
            for ax in axes[:, 0]:
                ax.set_ylabel(ylab, fontsize=8, color=GREY)
            for ax in axes[-1, :]:
                ax.set_xlabel('offered load (flits/node/cycle)', fontsize=8, color=GREY)
            h, l = axes.flat[0].get_legend_handles_labels()
            fig.legend(h, l, loc='lower center', ncol=10, frameon=False, fontsize=10, handlelength=2.2, columnspacing=1.4)
            fig.tight_layout(rect=(0, 0.06 if rows == 3 else 0.08, 1, 1), h_pad=0.6, w_pad=0.8)
            fig.savefig(out / f'{stage}_k{k}_{fname}.png', facecolor='white'); plt.close(fig)
            print('wrote', out / f'{stage}_k{k}_{fname}.png')


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    for stage in ('nt', 'g6'):
        draw(stage, out)


if __name__ == '__main__':
    main()
