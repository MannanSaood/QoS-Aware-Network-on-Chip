"""Block diagrams for report chapters 7 and 8 (module map, integration flow, deployment).

usage: python scripts/report_diagrams.py OUT_DIR
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

NAVY, INK, GREY, PALE, RED, PALE_RED = '#002060', '#17243A', '#516070', '#EAF0F7', '#C00000', '#FBE3E3'
plt.rcParams.update({'font.family': 'Times New Roman', 'savefig.dpi': 220})


def H(n):
    return 0.62 + 0.26 * n


def box(ax, x, top, w, title, lines=(), fc=PALE, ec=NAVY, tc=NAVY, size=11):
    h = H(len(lines))
    ax.add_patch(FancyBboxPatch((x, top - h), w, h, boxstyle='round,pad=0.02,rounding_size=0.08', fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, top - 0.14, title, ha='center', va='top', fontsize=size, fontweight='bold', color=tc)
    for i, l in enumerate(lines):
        ax.text(x + w / 2, top - 0.46 - i * 0.26, l, ha='center', va='top', fontsize=size - 2, color=INK)
    return top - h


def arrow(ax, a, b, text=None, rad=0.0, at=None, ha='center'):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=13, lw=1.2, color=GREY,
                                 connectionstyle=f'arc3,rad={rad}', shrinkA=2, shrinkB=2))
    if text:
        x, y = at or ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12)
        ax.text(x, y, text, ha=ha, va='bottom', fontsize=8.5, color=GREY, style='italic',
                bbox=dict(fc='white', ec='none', pad=0.5))


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis('off')
    return fig, ax


def modules(out):
    fig, ax = canvas(10, 5.6)
    W = 2.5; X = (0.2, 3.75, 7.3)
    box(ax, X[0], 5.4, W, 'Traffic and traces', ['Synthetic generators (19 patterns)', 'Netrace PARSEC converter', 'cycle · src · dst · class'])
    b_core = box(ax, X[1], 5.4, W, 'BookSim QoS core (frozen)', ['Input-queued mesh router', '2 classes × 2 VCs × 8 flits', 'Weighted 3:1 class service', 'Credit flow control, metrics'])
    box(ax, X[2], 5.4, W, 'Routing modules', ['XY, Odd-Even, West-First', 'DyAD-OE, TOPSIS-OE, Duato', 'DBAR, Footprint, O1TURN', 'SAQR-C (ours): column', 'tracker + XY / soft-O1TURN'], fc=PALE_RED, ec=RED, tc=RED)
    box(ax, X[0], 2.75, W, 'Run harness', ['Config + env whitelist', 'Frozen protocol / hashes', 'JSON result receipts'])
    box(ax, X[1], 2.75, W, 'Validation', ['Unit tests (90 M+ checks)', 'Runtime CTY / escape invariants', 'Deadlock check, RTL equivalence', 'Reproduction gate'])
    box(ax, X[2], 2.75, W, 'Evaluation and reporting', ['Pre-registered evaluators', 'Paired statistics over seeds', 'Verdicts, tables, figures'])
    arrow(ax, (X[0] + W, 4.75), (X[1], 4.75), 'demand trace')
    arrow(ax, (X[2], 4.45), (X[1] + W, 4.45), 'route set')
    arrow(ax, (X[0] + W / 2, 2.75), (X[0] + W / 2, 5.4 - H(3)), 'launches', at=(X[0] + W / 2 + 0.1, 3.05), ha='left')
    arrow(ax, (X[0] + W, 2.2), (X[1] + 0.3, b_core), 'config + run', at=(X[0] + W + 0.12, 3.0), ha='left')
    arrow(ax, (X[1] + W / 2, b_core), (X[1] + W / 2, 2.75), 'checked by', at=(X[1] + W / 2 + 0.1, 2.85), ha='left')
    arrow(ax, (X[1] + W, 1.85), (X[2], 1.85), 'receipts')
    fig.savefig(out / 'fig7_1_modules.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


def flow(out):
    fig, ax = canvas(10, 2.25)
    steps = [('Freeze', ['protocol + hashes']), ('Bundle', ['byte-exact inputs']), ('Gate', ['bit-for-bit repro']),
             ('Lanes', ['20–40 parallel', '≤ 5 h per wave']), ('Merge', ['receipts, status', 'alerts']),
             ('Evaluate', ['frozen criteria']), ('Report', ['verdict, figures'])]
    w, gap = 1.2, 0.22
    for i, (t, l) in enumerate(steps):
        x = 0.1 + i * (w + gap); hot = t == 'Lanes'
        box(ax, x, 1.95, w, t, l, size=10.5, fc=PALE_RED if hot else PALE, ec=RED if hot else NAVY, tc=RED if hot else NAVY)
        if i:
            arrow(ax, (x - gap, 1.45), (x, 1.45))
    ax.text(5, 0.25, 'A failed check stops the chain at that step: no receipt is accepted, an ALERT is raised and the run fails visibly.',
            ha='center', fontsize=11, color=GREY, style='italic')
    fig.savefig(out / 'fig7_2_integration.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


def deployment(out):
    fig, ax = canvas(10, 5.0)
    box(ax, 0.2, 4.8, 2.6, 'Developer workstation', ['Windows 11 + WSL Ubuntu', 'design, unit tests', 'freeze + bundle'])
    box(ax, 3.7, 4.8, 2.6, 'GitHub repository', ['code branch + bundle', 'workflows on master', 'results branches'])
    box(ax, 7.2, 4.8, 2.6, 'Netrace server (UT Austin)', ['library + PARSEC traces', 'hash-checked download'], fc='#F4F4F4', ec=GREY, tc=INK)
    box(ax, 0.2, 2.35, 4.3, 'GitHub Actions: build workflow', ['ubuntu-24.04 runner', 'compile 4 BookSim binaries', 'all unit tests, deadlock check', 'Icarus RTL equivalence, Yosys synthesis'])
    box(ax, 5.0, 2.35, 4.8, 'GitHub Actions: held-out waves', ['prepare → gate → lanes → merge', '20–40 parallel lanes per wave', 'checkpoint before the 6 h limit; cron every 6 h', 'Netrace conversion job'], fc=PALE_RED, ec=RED, tc=RED)
    arrow(ax, (2.8, 4.35), (3.7, 4.35), 'git push')
    arrow(ax, (3.7, 3.95), (2.8, 3.95), 'fetch, evaluate', at=(3.25, 3.48))
    arrow(ax, (4.3, 4.8 - H(3)), (2.6, 2.35), 'dispatch', at=(3.1, 2.75))
    arrow(ax, (5.3, 4.8 - H(3)), (6.4, 2.35), 'dispatch / cron', at=(5.25, 2.6), ha='left')
    arrow(ax, (7.4, 2.35), (6.0, 4.8 - H(3)), 'receipts', rad=0.25, at=(7.05, 2.85), ha='left')
    arrow(ax, (8.5, 4.8 - H(2)), (8.5, 2.35), 'traces', at=(8.6, 2.75), ha='left')
    fig.savefig(out / 'fig8_1_deployment.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    modules(out); flow(out); deployment(out)
    print('ok')
