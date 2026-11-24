"""Block diagrams for the report: chapters 1 and 4 (architecture, router, SAQR-C) and 7-8 (modules, integration, deployment).

usage: python scripts/report_diagrams.py OUT_DIR
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Rectangle, Circle

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


def evolution(out):
    fig, ax = canvas(10, 3.3)
    W = 2.75
    box(ax, 0.1, 3.1, W, 'Phase 1 baseline', ['Five-port RTL router (N, E, S, W, L)', 'XY routing, two VCs', 'Strict-priority QoS, credits', 'Simulation proof of concept'])
    box(ax, 3.625, 3.1, W, 'Phase 2 evaluation framework', ['BookSim QoS core, 4 VCs × 8 flits', 'Weighted 3:1 class service', 'XY, DyAD-OE, TOPSIS-OE', '4×4 to 32×32, 3,888 runs'])
    box(ax, 7.15, 3.1, W, 'Final algorithm: SAQR-C', ['Turn-column convergence cue', 'XY or soft-O1TURN per packet', 'Nine comparators, held-out G6', 'PARSEC traces, RTL classifier'], fc=PALE_RED, ec=RED, tc=RED)
    arrow(ax, (2.85, 2.2), (3.625, 2.2), 'measure')
    arrow(ax, (6.375, 2.2), (7.15, 2.2), 'design')
    ax.text(5, 1.05, 'Each stage keeps the previous one as a frozen, reproducible comparison point.', ha='center', fontsize=10, color=GREY, style='italic')
    ax.set_ylim(0.85, 3.3)
    fig.savefig(out / 'fig1_1_evolution.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


def eval_path(out):
    fig, ax = canvas(10, 3.6)
    W, gap = 2.1, 0.43
    top = [('Scenario configuration', ['mesh, traffic, load, seed']), ('Demand generation', ['immutable trace, hashed']),
           ('Source queues', ['per-class injection']), ('Router + link simulation', ['BookSim QoS core'])]
    bot = [('Figures and verdicts', ['frozen criteria']), ('Aggregation', ['paired statistics']),
           ('Validation', ['integrity, invariants']), ('Event and counter log', ['latency, flits, occupancy'])]
    for i, (t, l) in enumerate(top):
        x = 0.15 + i * (W + gap); box(ax, x, 3.4, W, t, l, size=10.5)
        if i: arrow(ax, (x - gap, 2.95), (x, 2.95))
    for i, (t, l) in enumerate(bot):
        x = 0.15 + i * (W + gap); hot = t.startswith('Figures')
        box(ax, x, 1.55, W, t, l, size=10.5, fc=PALE_RED if hot else PALE, ec=RED if hot else NAVY, tc=RED if hot else NAVY)
        if i: arrow(ax, (x, 1.1), (x - gap, 1.1))
    xr = 0.15 + 3 * (W + gap) + W / 2
    arrow(ax, (xr, 3.4 - H(1)), (xr, 1.55), 'per cycle', at=(xr + 0.08, 2.15), ha='left')
    fig.savefig(out / 'fig4_1_eval_path.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


def router(out):
    fig, ax = canvas(10, 5.6)
    ports = ['North', 'East', 'South', 'West', 'Local']
    CRIT, BE = '#C9D7EE', '#E4E4E4'
    for i, pn in enumerate(ports):
        y = 4.75 - i * 0.95
        ax.add_patch(FancyBboxPatch((0.2, y - 0.3), 2.3, 0.72, boxstyle='round,pad=0.02,rounding_size=0.06', fc='white', ec=NAVY, lw=1.1))
        ax.text(0.32, y + 0.24, f'{pn} input', fontsize=9.5, fontweight='bold', color=NAVY, va='center')
        for v in range(4):
            ax.add_patch(Rectangle((0.32 + v * 0.53, y - 0.22), 0.46, 0.3, fc=CRIT if v < 2 else BE, ec=GREY, lw=0.7))
            ax.text(0.55 + v * 0.53, y - 0.07, f'VC{v}', ha='center', va='center', fontsize=7.5, color=INK)
        arrow(ax, (2.5, y + 0.05), (3.15, y + 0.05))
    b1 = box(ax, 3.15, 5.35, 3.0, 'Route unit', ['baseline route function, or', 'SAQR-C: column tracker,', 'XY / soft-O1TURN choice'], fc=PALE_RED, ec=RED, tc=RED, size=10.5)
    b2 = box(ax, 3.15, 3.3, 3.0, 'VC allocator', ['class-restricted VC pools'], size=10.5)
    b3 = box(ax, 3.15, 2.05, 3.0, 'Switch allocator', ['weighted 3:1 critical / best effort', 'oldest first within a class'], size=10.5)
    arrow(ax, (4.65, b1), (4.65, 3.3)); arrow(ax, (4.65, b2), (4.65, 2.05))
    ax.add_patch(FancyBboxPatch((6.75, 0.7), 1.25, 4.6, boxstyle='round,pad=0.02,rounding_size=0.06', fc=PALE, ec=NAVY, lw=1.2))
    ax.text(7.375, 3.0, '5 × 5\ncrossbar', ha='center', va='center', fontsize=11, fontweight='bold', color=NAVY)
    arrow(ax, (6.15, 1.4), (6.75, 1.4), 'grant')
    for i, pn in enumerate(ports):
        y = 4.75 - i * 0.95
        arrow(ax, (8.0, y + 0.05), (8.55, y + 0.05))
        ax.text(8.62, y + 0.05, f'{pn} output', fontsize=9.5, color=INK, va='center')
    arrow(ax, (9.2, 0.45), (1.35, 0.45), 'credits returned from downstream routers', at=(5.3, 0.5))
    ax.add_patch(Rectangle((0.3, 0.02), 0.25, 0.14, fc=CRIT, ec=GREY, lw=0.6)); ax.text(0.6, 0.09, 'critical class (VC0–1)', fontsize=8.5, va='center', color=INK)
    ax.add_patch(Rectangle((2.4, 0.02), 0.25, 0.14, fc=BE, ec=GREY, lw=0.6)); ax.text(2.7, 0.09, 'best-effort class (VC2–3), 8 flits per VC', fontsize=8.5, va='center', color=INK)
    fig.savefig(out / 'fig4_2_router.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


def pipeline(out):
    fig, ax = canvas(10, 2.6)
    st = [('Buffer write +\nroute compute', ['head flit decoded', 'SAQR-C tracker update']), ('VC allocation', ['class VC pool', 'escape VC kept free']),
          ('Switch allocation', ['weighted 3:1', 'oldest first']), ('Switch traversal', ['5 × 5 crossbar']), ('Link traversal', ['credit returned'])]
    w, gap = 1.7, 0.33
    for i, (t, l) in enumerate(st):
        x = 0.1 + i * (w + gap); hot = i == 0
        ax.add_patch(FancyBboxPatch((x, 0.75), w, 1.45, boxstyle='round,pad=0.02,rounding_size=0.08',
                                    fc=PALE_RED if hot else PALE, ec=RED if hot else NAVY, lw=1.2))
        ax.text(x + w / 2, 2.12, t, ha='center', va='top', fontsize=10.5, fontweight='bold', color=RED if hot else NAVY, linespacing=1.0)
        for k, line in enumerate(l):
            ax.text(x + w / 2, 1.33 - k * 0.24, line, ha='center', va='top', fontsize=8.8, color=INK)
        if i: arrow(ax, (x - gap, 1.47), (x, 1.47))
    ax.text(5, 0.3, 'One-cycle routing-delay model for every algorithm; SAQR-C decides at injection and adds no pipeline stage.',
            ha='center', fontsize=9.5, color=GREY, style='italic')
    fig.savefig(out / 'fig4_3_pipeline.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


def saqr_decision(out):
    fig, ax = canvas(10, 4.6)
    box(ax, 0.2, 4.4, 3.0, 'Transit head flit', ['arrives from a neighbour', 'with X distance still to cover'], size=10.5)
    box(ax, 0.2, 2.55, 3.0, 'Column tracker (per router)', ['candidate column register', '12-bit share f of that column', 'hysteresis bit: converging'], fc=PALE_RED, ec=RED, tc=RED, size=10.5)
    arrow(ax, (1.7, 4.4 - H(2)), (1.7, 2.55), 'update', at=(1.78, 3.05), ha='left')
    box(ax, 3.75, 4.4, 2.5, 'Packet injected here', ['destination column known'], size=10.5)
    cx, cy = 5.0, 2.05
    ax.add_patch(Polygon([(cx, cy + 0.85), (cx + 1.35, cy), (cx, cy - 0.85), (cx - 1.35, cy)], closed=True, fc='white', ec=NAVY, lw=1.2))
    ax.text(cx, cy, 'converging and\ndestination column =\ncandidate column?', ha='center', va='center', fontsize=9.5, color=NAVY, linespacing=1.15)
    arrow(ax, (5.0, 4.4 - H(1)), (5.0, cy + 0.85))
    arrow(ax, (3.2, 1.55), (cx - 1.05, cy - 0.2), 'state', at=(3.35, 1.25), ha='left')
    box(ax, 7.1, 3.55, 2.7, 'Adaptive: soft-O1TURN', ['XY or YX plan per packet', 'YX hops use VC1 only'], fc=PALE_RED, ec=RED, tc=RED, size=10.5)
    box(ax, 7.1, 1.35, 2.7, 'Deterministic: exact XY', ['both VCs of the class'], size=10.5)
    arrow(ax, (cx + 1.0, cy + 0.3), (7.1, 3.0), 'yes', at=(6.55, 2.75))
    arrow(ax, (cx + 1.0, cy - 0.3), (7.1, 0.95), 'no', at=(6.55, 1.0))
    ax.text(5, 0.1, 'Spread columns (bit complement, tornado, random flows) keep packets on XY; converging rows (transpose, bit reversal) go adaptive.',
            ha='center', fontsize=9, color=GREY, style='italic')
    fig.savefig(out / 'fig4_4_saqr_c.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


def route_sets(out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
    for ax, title, yx in ((axes[0], 'Exact XY (deterministic packets)', False), (axes[1], 'Soft-O1TURN, YX plan (adaptive packets)', True)):
        ax.set_xlim(-0.9, 3.6); ax.set_ylim(-0.9, 3.6); ax.axis('off'); ax.set_aspect('equal')
        for i in range(4):
            ax.plot([0, 3], [i, i], color='#C8D0DC', lw=1, zorder=1); ax.plot([i, i], [0, 3], color='#C8D0DC', lw=1, zorder=1)
        for x in range(4):
            for y in range(4):
                ax.add_patch(Circle((x, y), 0.13, fc='white', ec=GREY, lw=0.9, zorder=2))
        ax.add_patch(Circle((0, 0), 0.17, fc=NAVY, ec=NAVY, zorder=3)); ax.text(0.2, -0.4, 'source', fontsize=9, color=NAVY)
        ax.add_patch(Circle((3, 3), 0.17, fc=NAVY, ec=NAVY, zorder=3)); ax.text(2.35, 3.3, 'destination', fontsize=9, color=NAVY)
        ax.set_title(title, fontsize=11.5, fontweight='bold', color=NAVY)
        if not yx:
            ax.plot([0, 3, 3], [0, 0, 3], color=NAVY, lw=3, zorder=2.5)
            ax.text(1.5, -0.75, 'X first, then Y: on VC0 or VC1', ha='center', fontsize=9.5, color=INK)
        else:
            ax.plot([0, 0], [0, 2], color=RED, lw=3, zorder=2.5)
            ax.plot([0, 3, 3], [2, 2, 3], color=NAVY, lw=3, ls='--', zorder=2.5)
            ax.text(-0.25, 1.0, 'Y hops\nVC1 only', fontsize=9, color=RED, ha='right', va='center')
            ax.text(1.5, 2.3, 'escape: continue XY on VC0', fontsize=9, color=NAVY, ha='center', va='bottom')
            ax.text(1.5, -0.75, 'a packet can always fall back to the XY escape VC', ha='center', fontsize=9.5, color=INK)
    fig.text(0.5, 0.01, 'VC0 carries only XY hops, so its channel graph is acyclic (Duato): the adaptive VC1 can never deadlock the network.',
             ha='center', fontsize=10, color=GREY, style='italic')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out / 'fig4_5_route_sets.png', bbox_inches='tight', facecolor='white'); plt.close(fig)


if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    modules(out); flow(out); deployment(out)
    evolution(out); eval_path(out); router(out); pipeline(out); saqr_decision(out); route_sets(out)
    print('ok')
