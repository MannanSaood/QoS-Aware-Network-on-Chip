# Corrected DyAD and longer BookSim comparison

This protocol was specified before inspecting the new comparison results. No
thresholds, TOPSIS weights or hardware resources are selected to defeat XY.
The former 2,160-run data and figures remain in `primary_grid` and
`primary_report`; their original implementation and binary are preserved in
`results/legacy_primary_implementation`.

## Implementation

DyAD-OE now declares a valid neighboring port congested when **any downstream
virtual-channel FIFO is at least 60% occupied**. The previous implementation
averaged four VCs for the trigger, allowing one full VC to appear only 25% full.
Once triggered, DyAD still chooses minimum aggregate occupancy among legal
odd-even minimal outputs. Both modes obey the same odd-even restrictions.
This is a documented multi-VC adaptation, not an exact reproduction of the
original single-FIFO DyAD experiment. The 60% threshold is unchanged.

TOPSIS-OE retains vector normalization, cost criteria of aggregate occupancy
and maximum VC occupancy, normalized weights 0.7/0.3, ideal/anti-ideal Euclidean
distances and relative closeness. Equal scores retain deterministic candidate
order. It is the project's specified TOPSIS routing policy, not a claim to
reproduce an unspecified published TOPSIS router. Tests independently check
a hand-calculated conflicting-criteria example, dominance, scale invariance,
weight normalization and the single-criterion reduction. No ranking weights
were tuned. Both adaptive policies still make one output decision at routing
time and can wait for that selected output at VC allocation.

The user-identified reference is [Yu et al., Scientific Reports 2025,
doi:10.1038/s41598-025-20381-3](https://www.nature.com/articles/s41598-025-20381-3).
This study does **not** reproduce that implementation. Correctness checks here
validate the specified project selector, not fidelity to that paper. No outcome
of this sweep establishes that the paper's data are correct or fabricated.
An exact reproduction would be a separately specified experiment; changing the
selector midway through this sweep would invalidate the controlled comparison.

## Experiment

4x4, 8x8, 16x16 and 32x32; uniform, coordinate-swap transpose, 50%-duty Markov
bursty uniform and three fixed mixed-hotspot locations. Each hotspot receives
20% targeted traffic plus its share of the 80% uniform traffic. Self traffic is
included consistently. Three seeds, nine load points per mesh/traffic, three
policies: **1,944 actual BookSim runs**. Each has 5,000 warm-up and 20,000 measured
cycles. Five-flit packets, four VCs, eight flits/VC and identical allocator,
pipeline and link settings across algorithms. Routing latency is one modeled
cycle for each; these results do not measure TOPSIS hardware timing or area.

Uniform/transpose/bursty loads are `(4/k)*[.02,.05,.1,.2,.3,.4,.6,.8,1]`.
The uniform bisection necessary bound sets the sampling scale, not a claim
about actual saturation or the bounds of the other traffic patterns.
Hotspot loads are `[.1,.25,.5,.7,.85,1,1.15,1.5,2]/(.2*k*k+.8)`; their reference
is the necessary shared-ejection capacity bound. Loads are rounded to 12
significant digits. Each algorithm receives exactly the same load grid.
The old 0.1--1.0 stress sweep remains available; these additional points reveal
the previously missing low-load and transition behavior on larger meshes.

Native BookSim traffic generators use matched seed IDs. Backpressure and global
RNG consumption can produce different realized packet traces across policies;
seed matching is not trace replay. Three seeds provide an initial uncertainty
estimate, not a proof of equivalence. Protocol, binary hash, configurations,
raw metric JSON and simulator logs are preserved; cache reuse requires the
same binary hash and experiment metadata.

## Interpretation and plots

Separate p99 latency, delivered throughput and congested port-time figures.
Keep all 72 individual charts and the agreed 10 six-panel comparison pages;
no presentation is modified. Lines have no dot markers. Individual charts
include 95% t-intervals of seed-level statistics. Actual fractional offered
loads are retained, with panel-specific ranges clearly labeled.
P99 uses a labeled logarithmic y-axis so both low-load latency and large
overload growth remain readable. Throughput and congestion use linear y-axes
starting at zero. This changes presentation only, not measured values.

P99 covers completed packets and includes source queuing. It is not an
uncensored steady-state latency estimate. First/second-half delivery counts
and p99 expose temporal drift: flag p99 growth above 25% or throughput change
above 10%; separately flag fewer than 1,000 completed packets. These are
diagnostics, not formal stationarity tests. Read p99 with throughput and these
flags, especially above saturation. Congestion retains the old definition:
fraction of sampled physical input-port time with aggregate buffer occupancy
at least 60%; it excludes source backlog. It is intentionally distinct from
DyAD's per-VC trigger and is measured identically for all policies.

Better means lower latency, higher delivered throughput at a common offered
load, and lower congestion only when delivery is comparable. No guaranteed
ordering of XY, DyAD-OE and TOPSIS-OE is assumed.
