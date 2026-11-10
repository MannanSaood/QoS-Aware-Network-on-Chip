"""Per-mesh figures for the SAQR held-out studies, in the layout of the phase-1 deck:
for every mesh, one figure per metric (critical-class p99 latency, total delivered throughput,
congested port-time), one panel per traffic pattern, one line per route, means over seeds.
Linear axes from zero, no markers, no smoothing.

usage: python scripts/plot_saqr_study.py {g5|g6|g7|nt} [out_dir] [--only CANDIDATE]
  g5  G5 receipts plus the O1TURN stage (seeds 301-305)
  g6  G6 receipts (seeds 401-405)
  g7  G7 receipts (seeds 501-505)
  nt  Netrace PARSEC traces on 8x8 (simulator seeds 601-603)
  --only CANDIDATE   draw the nine comparators and this one candidate only
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / 'results/saqr_study'
METRICS = [('crit_p99', 'Critical-class p99 latency (cycles)', 'Lower is better; check pending demand', 'p99_latency'),
           ('throughput', 'Delivered throughput (flits/node/cycle)', 'Higher is better', 'throughput'),
           ('congested', 'Congested port-time (%)', 'Ports with input buffers >= 60 % full; read with throughput', 'congestion')]
LABEL = {'xy': 'XY', 'oefixed': 'Odd-Even', 'dyad': 'DyAD-OE', 'topsis': 'TOPSIS-OE', 'duato': 'Duato', 'westfirst': 'West-First',
         'dbar': 'DBAR-style', 'footprint': 'Footprint-style', 'o1turn': 'O1TURN', 'saqr_sc': 'SAQR-SC', 'saqr_h': 'SAQR-H', 'saqr_c': 'SAQR-C',
         'saqr_ct': 'SAQR-CT'}
COLOR = {'xy': '#0072B2', 'oefixed': '#56B4E9', 'dyad': '#D55E00', 'topsis': '#009E73', 'duato': '#CC79A7', 'westfirst': '#999999',
         'dbar': '#E69F00', 'footprint': '#8C564B', 'o1turn': '#6A3D9A', 'saqr_sc': '#F0E442', 'saqr_h': '#555555', 'saqr_c': '#C00000',
         'saqr_ct': '#C00000'}
TITLE = {'uniform': 'Uniform', 'transpose': 'Transpose', 'bursty': 'Bursty on/off', 'hotspot_corner': 'Hotspot: corner',
         'hotspot_edge': 'Hotspot: edge', 'hotspot_center': 'Hotspot: center', 'bitcomp': 'Bit complement', 'bitrev': 'Bit reversal',
         'shuffle': 'Shuffle', 'tornado': 'Tornado', 'neighbor': 'Neighbor', 'multiflow': 'Multi-flow (4 dests)',
         'mixed': 'Mixed (50 % transpose)', 'butterfly': 'Butterfly', 'randperm': 'Random permutation',
         'antitranspose': 'Anti-transpose (unseen)', 'unshuffle': 'Unshuffle (unseen)',
         'nt_blackscholes': 'PARSEC blackscholes', 'nt_fluidanimate': 'PARSEC fluidanimate', 'nt_x264': 'PARSEC x264'}
SEEDS_NOTE = {'g5': 'seeds 301-305, held-out G5', 'g6': 'seeds 401-405, fresh held-out G6', 'g7': 'seeds 501-505, fresh held-out G7',
              'nt': 'Netrace PARSEC traces, simulator seeds 601-603'}


def metrics(r):
    c, b = r['qos']['classes']
    return dict(throughput=(c['ejected_flits'] + b['ejected_flits']) / (r['cycles'] * r['k'] ** 2),
                crit_p99=c['latency_p99_cycles'], congested=r['aggregate']['congested_port_time_pct'])


def load(stage):
    if stage in ('g6', 'g7', 'nt'):
        proto = json.loads((S / stage / 'protocol.json').read_text())
        routes = {r: S / stage for r in proto['comparators'] + proto['candidates']}
    else:
        proto = json.loads((S / 'g5/protocol.json').read_text())
        routes = {r: S / 'g5' for r in proto['comparators'] + ['saqr_sc', 'saqr_h']}
        routes['o1turn'] = S / 'g5_o1t'
    acc = defaultdict(list)
    for c in proto['cases']:
        for r, base in routes.items():
            f = base / 'cases' / c['name'] / f'weighted_{r}' / 'result.json'
            acc[(c['k'], c['traffic'], c['load'], r)].append(metrics(json.loads(f.read_text())))
    return proto, list(routes), acc


def main():
    args = sys.argv[1:]
    only = None
    if '--only' in args:
        i = args.index('--only'); only = args[i + 1]; del args[i:i + 2]
    stage = args[0]
    out = Path(args[1]) if len(args) > 1 else ROOT / 'docs/figures' / (stage + (f'_{only}' if only else ''))
    out.mkdir(parents=True, exist_ok=True)
    proto, routes, acc = load(stage)
    if only:
        routes = [r for r in routes if not r.startswith('saqr') or r == only]
    main_route = only or ('saqr_c' if stage == 'g6' else 'saqr_ct' if 'saqr_ct' in routes else 'saqr_h')
    seeds = len(proto['seeds'])
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titlesize': 9, 'figure.dpi': 110, 'savefig.dpi': 170})
    traffic = proto['traffic']
    cols = 5 if len(traffic) > 4 else len(traffic) + 1; rows = -(-len(traffic) // cols)
    for k in proto['meshes']:
        for key, ylabel, note, fname in METRICS:
            fig, axes = plt.subplots(rows, cols, figsize=(17, 3.1 * rows + .9), layout='constrained')
            for ax, t in zip(axes.flat, traffic):
                for r in routes:
                    pts = sorted((ld, sum(m[key] for m in v) / len(v)) for (kk, tt, ld, rr), v in acc.items() if kk == k and tt == t and rr == r)
                    cand = r.startswith('saqr')
                    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=COLOR[r], label=LABEL[r],
                            linewidth=2.6 if r == main_route else (1.6 if cand else 1.1),
                            linestyle='-' if cand or r == 'xy' else '--', zorder=3 if cand else 2)
                ax.set_title(TITLE.get(t, t)); ax.set_xlim(left=0); ax.set_ylim(bottom=0)
                ax.grid(alpha=.18); ax.set_axisbelow(True)
                ax.set_xlabel('Offered load (flits/node/cycle)', fontsize=7)
            for ax in axes.flat[len(traffic):]: ax.axis('off')
            axes.flat[0].set_ylabel(ylabel, fontsize=7)
            h, l = axes.flat[0].get_legend_handles_labels()
            spare = axes.flat[len(traffic)] if len(axes.flat) > len(traffic) else None
            if spare is not None: spare.legend(h, l, loc='center', frameon=False, fontsize=9, ncol=2)
            else: fig.legend(h, l, loc='outside lower center', ncol=6, frameon=False)
            fig.suptitle(f'{k}x{k}: {ylabel.split(" (")[0]}  |  {k*k} nodes, weighted QoS, {seeds}-seed means '
                         f'({SEEDS_NOTE[stage]})  |  {note}', fontsize=10)
            fig.savefig(out / f'k{k}_{fname}.png'); plt.close(fig)
            print('wrote', out / f'k{k}_{fname}.png')


if __name__ == '__main__':
    main()
