# Research-grounded college report

## Simulator roles

BookSim is the primary model for algorithm and scalability conclusions. NS-2 is
a secondary, explicitly coarser packet model. Run both; present the NoC results
from BookSim, with NS-2 measurements and a model-capacity comparison separately.
Disagreement between models is not a numerical accuracy measurement.

## Four traffic sections

1. **Uniform:** Bernoulli injection and uniformly distributed destinations.
2. **Transpose:** Bernoulli injection, destination (x,y) -> (y,x). This is a
   spatial communication pattern, not intermittent/on-off injection. It differs
   from the complement-style pattern called transpose1 in the original DyAD paper.
3. **Bursty on/off:** uniform destinations, independent two-state injection per
   source. OFF->ON and ON->OFF probabilities are both 0.02 per cycle; mean ON and
   OFF duration 50 cycles, stationary duty factor 50%. During ON the packet
   injection probability is twice the configured mean; during OFF it is zero.
   This is a Markov burst model, not a claim to reproduce self-similar application traces.
4. **Hotspot locations:** three separate fixed-location cases: corner (0,0), edge
   midpoint (k/2,0), center (k/2,k/2). In the 8x8 load sweep these are router IDs
   0, 4 and 36. Twenty percent of packets explicitly target the hotspot; the
   remaining 80% have uniform destinations, so total hotspot probability is
   0.2 + 0.8/(k*k). The mixture and total injection remain fixed across locations.

All location runs are independent experiments. A hotspot moving during a single
run would test adaptation/recovery, and is not included here. A separate
100%-center-hotspot diagnostic tests the shared ejection-capacity constraint.
Raw location-to-location latency also reflects geometry: mean hop distance and
available ingress directions change between corner, edge and center. Judge
routing improvement against XY within the same location first.

## Which metrics matter?

| Metric | Report use | How to interpret it |
|---|---|---|
| p50 latency | Summary table | Typical completed-packet delay; lower is desirable at comparable delivered traffic. |
| p90 latency | Summary table | Slow-packet behavior beyond the median. |
| p99 latency | Separate line figure | Tail behavior, especially for burstiness and congestion. Unfinished packets are excluded. |
| Delivered throughput | Separate line figure | Flits/node/cycle; higher is desirable for the same offered load. |
| Congested port-time | Separate line figure | Fraction of sampled ports at least 60% full. Explains widespread queue pressure; it is not packet loss. |
| Peak physical-link utilization | Summary table | Reveals the busiest inter-router link. High utilization may mean useful work or a bottleneck; assess throughput alongside it. |
| Mean latency | Summary table | Supports comparison with the papers' conventional load–mean-latency results without another near-duplicate chart. |
| Delivered/offered traffic | Summary table | Indicates unmet demand; a finite-window rate ratio, not delivery probability or energy efficiency. |
| Packet drops | NS-2 summary table | DropTail loss. BookSim's credit-based model is lossless; source backlog still matters. |
| Saturation injection rate | Future longer-run table | Bracket the knee with finer loads and test stationarity/window-length sensitivity. Do not infer a precise sustained capacity from a short saturated run. |

The primary grid covers ten loads (0.1–1.0), four meshes (4/8/16/32), six traffic
cases, three policies and three seeds: 2160 BookSim runs. p99 and throughput
produce 48 individual charts. Eight comparison pages each combine six traffic
cases for one metric and mesh. Two congestion pages cover 4x4 and 32x32 with
all six traffic cases; the individual chart library retains all 24 congestion
charts, for 72 total. PowerPoint work is paused; this pipeline produces results
and standalone figures only.

All figures contain a single metric, actual sampled load/size coordinates,
straight connecting lines without dot markers and consistent policy styles.
Individual figures add three-seed 95% t-intervals; comparison pages show the
means and refer to those intervals. No offsets or invented separation. Small differences
can be inspected in the individual figures and relative-to-XY tables. Comparison
panels each start at zero and use their own measured y-range, explicitly labelled;
compare algorithms within a traffic panel rather than comparing line heights
across panels with different scales. This keeps a small hotspot throughput from
being compressed by a much larger uniform-traffic throughput. Small differences
are retained numerically in `primary_report/summary.csv`. Overlapping intervals are not evidence
of a significant win. Lower congestion/utilization alone is not an algorithm win.
`descriptive_leaders.csv` gives descriptive leaders; `relative_to_xy.csv` gives percent
changes and counts of better/equal/worse outcomes across the three seed cases.
For latency negative change is desirable; for throughput positive is desirable.
These seed counts describe consistency; they are not significance tests.

## Evidence from primary papers

- [Hu & Marculescu, DyAD, DAC 2004](https://www.cs.york.ac.uk/rts/docs/SIGDA-Compendium-1994-2004/papers/2004/dac04/pdffiles/p260.pdf)
  evaluates average source-inclusive packet latency and sustainable throughput
  under several traffic patterns, plus hardware implementation overhead. It
  explicitly reports that XY can beat local adaptive methods under uniform traffic.
- [Gratz et al., Regional Congestion Awareness, HPCA 2008](https://www.cs.utexas.edu/~skeckler/pubs/hpca08.pdf)
  uses load–latency curves and saturation bandwidth, and tests mesh size, packet
  length and VC count. Its operational saturation definition is three times
  zero-load average latency; that definition must be stated if adopted, rather
  than silently equating a short-run maximum throughput with sustained capacity.
- [Fault-tolerant QoS/TOPSIS routing, Scientific Reports 2025](https://www.nature.com/articles/s41598-025-20381-3)
  evaluates delay/throughput with faults and also reports energy using explicit
  ORION activity-based modeling. Its fault handling and energy methodology are
  not present in this project's TOPSIS-OE selector; its published rankings cannot
  be transferred to this implementation.

## Metrics requiring additional implementation

Energy per delivered packet/flit requires calibrated buffer, allocator, crossbar
and link activity costs plus leakage and technology parameters. Routing-stage
latency/area require a hardware timing or synthesis model; CPU process runtime
does not supply them. Per-class fairness and deadline-miss ratios require actual
QoS classes, traffic demand accounting and deadlines. Fault tolerance requires
fault injection and recovery logic. These belong in future work until implemented
and validated, not fabricated "efficiency" plots.

All current policies use minimal paths, so route stretch is one by construction;
an extra hop-count comparison adds little. Completed-packet hop averages can
differ under saturation because different packets finish, not because paths detour.

## DyAD audit

`results/dyad_audit/audit.json` is a one-seed threshold diagnostic using a separate
instrumented binary. On 8x8 uniform traffic at load 0.3, threshold 0.6, 3,323 of
8,471 multi-candidate decisions (39.2%) had a VC above threshold while aggregate
occupancy remained below it. The adaptation nevertheless switched on 4,940
decisions. Lower thresholds improved this diagnostic; this is evidence of
sensitivity, not a proof of the best threshold or a complete explanation of every
ranking. The report comparisons retain the documented threshold of 0.6.

The reference DyAD paper uses FIFO congestion flags. Our four-VC aggregate
credit signal and equal per-policy routing delay make this a project adaptation.
Tests validate minimal paths and turn restrictions; they do not establish that
the adaptation replicates the paper's performance.
