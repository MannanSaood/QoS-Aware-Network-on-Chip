# Routing comparison audit

Audit date: 14 October 2026. The primary 2,160-run dataset and its graphs were
preserved. This audit examines why XY often leads, without tuning the study to
produce a preferred winner.

This is the **pre-fix audit** of the archived aggregate-trigger DyAD implementation.
The subsequent correction and longer comparison are documented in
[FAIR_COMPARISON_PROTOCOL.md](FAIR_COMPARISON_PROTOCOL.md), with simulator reproduction
checks in `results/fair_reproduction/validation.json`. The old audit script's
source-hash assertions deliberately reject the changed production headers;
its recorded results remain evidence for the archived implementation.

## Findings

No basic routing legality or TOPSIS arithmetic error was found by the checks
below. This is bounded validation, not proof of complete implementation fidelity
or a faithful reproduction of published DyAD/TOPSIS performance.

* All 720 source/traffic/load/seed cases have identical BookSim configurations
  across the three policies except the routing function. Their buffers, VCs,
  allocation settings, delays, packet sizes, traffic and seeds match.
* Algorithm source hashes match the completed study manifest and the headers
  copied into the simulator build. A separate instrumented build reproduced
  every network metric of 27 selected primary runs exactly.
* Routing tests passed 5,074 exhaustive source/destination cases, dependency-graph
  cycle checks through 8x8, and 150,000 routing trials through 32x32. These are
  not a formal whole-simulator or protocol deadlock proof.
* TOPSIS passed a hand-computed conflicting-criteria example and 10,000 feasible
  credit-state checks for cost dominance, scaling invariance and agreement with
  minimum-occupancy routing when only that criterion is weighted.
* The simulator adapter's observed credit pressures remained in valid ranges.

### Why XY can win

The original DyAD paper itself reports XY outperforming DyAD-OE and adaptive
odd-even under uniform traffic. It explains that local, short-term adaptive
choices need not preserve the traffic balance that XY obtains for this pattern.
This supports the possibility of XY winning; it does not validate the magnitude
of our measured differences. See Hu and Marculescu, DAC 2004, section 4.1:
https://www.cs.york.ac.uk/rts/docs/SIGDA-Compendium-1994-2004/papers/2004/dac04/pdffiles/p260.pdf

Our model gives every policy the same one-cycle routing stage. Therefore the
extra host CPU work of TOPSIS is not the reason for its simulated packet latency.

DyAD uses a 60% threshold over aggregate credit occupancy across four VCs, each
eight flits deep. A single congested VC can be diluted by other empty VCs. For
example, one full VC and three empty VCs gives only 25% aggregate occupancy.
The original paper used FIFO occupancy flags without this four-VC averaging.
The diagnostic below confirms sensitivity to this adaptation. Threshold changes
are different policy variants, not corrections proven to be universally better.

TOPSIS-OE is our project-defined selector: 70% aggregate occupancy and 30% peak
VC occupancy, with the same minimal odd-even candidates. It is not a reproduction
of a specific published TOPSIS NoC routing protocol. The tests establish particular
mathematical properties of the selector, not that these criteria/weights are optimal.

The integration chooses an output when the head flit is routed, before VC
allocation. It does not revisit that decision while waiting for allocation.
The local credit snapshot can therefore become outdated. The precise contribution
of this and other shared routing/allocation effects has not been isolated.

### Controlled simulator diagnostics

63 additional actual BookSim runs used 8x8 meshes, three seeds, 1,000 warm-up
cycles and 3,000 observation cycles. Only the diagnostic route selector changed.
All numbers below are three-seed means. Throughput is flits/node/cycle; p99 is
cycles. All variants remained within the same odd-even restrictions except XY.

| Uniform traffic variant | Throughput at 30% | p99 at 30% | Throughput at 50% | p99 at 50% |
|---|---:|---:|---:|---:|
| XY | 0.30210 | 120.3 | 0.35594 | 2108.3 |
| Fixed odd-even | 0.14614 | 2432.0 | 0.14290 | 3039.0 |
| Current DyAD, aggregate trigger 60% | 0.18497 | 2304.7 | 0.17310 | 3226.7 |
| Diagnostic DyAD, aggregate trigger 20% | 0.22687 | 1451.0 | 0.18735 | 2983.3 |
| Diagnostic DyAD, peak-VC trigger 60% | 0.25307 | 1383.7 | 0.19350 | 3132.7 |
| Always-adaptive minimum-occupancy odd-even | 0.30246 | 283.7 | 0.19169 | 3017.7 |
| Current TOPSIS-OE | 0.30241 | 191.7 | 0.18319 | 2977.0 |

Lowering DyAD's trigger from 60% to 20% raises mean throughput by about 22.7%
at 30% offered load. It does not remove the high-load gap. At 50% load, even
the simple always-adaptive selector has much lower throughput than XY, so the
loss is not unique to TOPSIS arithmetic or its second criterion. These are
diagnostics at selected operating points, not a new globally tuned baseline.
Transpose diagnostics are retained in the associated summary and raw files.

Evidence:
* `results/routing_comparison_audit/summary.csv`, `runs.json`, `validation.json`
* `results/routing_high_load_audit/summary.csv`, `runs.json`, `validation.json`
* `scripts/audit_routing_comparison.py` (default and `--high-load`)

### Limits that affect the rankings

The main sweep is a finite-window overload study, not a steady-state saturation
test. For the 20% mixed hotspot, the necessary single-destination ejection bound
is 1/(0.2N+0.8) flits/node/cycle. This is about 0.07353, 0.01923 and 0.004864 on
8x8, 16x16 and 32x32. Every main hotspot point on these meshes (0.1 through 1.0)
therefore exceeds that bound. The sweep misses their low-load operating region.

p99 includes only packets completed inside the observation window. Unfinished
packets can change the apparent ranking. Congestion is the percentage of sampled
inter-router input ports whose occupancy is at least 60%; it excludes source
backlog and the local injection input. Low congestion is not proof of high
throughput or low total system backlog.

Before claiming general superiority, select a reference-faithful DyAD policy and
explicit TOPSIS formulation, add a fine low-load sweep around each saturation
point, check longer windows and more seeds, and examine VC-allocation availability
and delayed route decisions. Do not select parameters solely to reverse a winner.

## Three main metric tables for the existing study

Each cell shows the policy with the most strict numerical first places across
the ten tested loads, followed by its count out of ten. Ties are excluded from
these counts. For the split 32x32 corner p99 result, all three counts are shown.
These are descriptive means, not significance tests, combined scores or measured
probabilities of winning. The complete values and uncertainty remain in
`results/primary_report/summary.csv`. DyAD/TOPSIS below mean our OE implementations.

### Throughput: higher is better

| Traffic | 4x4 | 8x8 | 16x16 | 32x32 |
|---|---|---|---|---|
| Uniform | XY (5/10) | XY (8/10) | XY (9/10) | XY (10/10) |
| Transpose | TOPSIS (9/10) | TOPSIS (9/10) | TOPSIS (10/10) | TOPSIS (10/10) |
| Bursty on/off | XY (5/10) | XY (8/10) | XY (9/10) | XY (10/10) |
| Corner hotspot | Close: DyAD (6/10) | XY (10/10) | XY (10/10) | DyAD (8/10) |
| Edge hotspot | Close: XY (4/10) | XY (10/10) | XY (10/10) | XY (10/10) |
| Center hotspot | Close: DyAD (5/10) | XY (10/10) | XY (10/10) | XY (10/10) |

For 4x4 hotspots the numerical throughput leads are small and variable; these
counts do not establish a clear winner. On uniform/bursty traffic, XY's strong
throughput advantage appears at heavier loads; tiny light-load leads should not
be interpreted as meaningful routing gains.

### p99 latency: lower is better

| Traffic | 4x4 | 8x8 | 16x16 | 32x32 |
|---|---|---|---|---|
| Uniform | XY (8/10) | XY (10/10) | XY (8/10) | XY (10/10) |
| Transpose | TOPSIS (10/10) | TOPSIS (10/10) | TOPSIS (10/10) | TOPSIS (6/10), XY (4/10) |
| Bursty on/off | XY (8/10) | XY (8/10) | XY (10/10) | XY (10/10) |
| Corner hotspot | TOPSIS (6/10) | XY (6/10) | XY (8/10) | DyAD (5/10), TOPSIS (4/10), XY (1/10) |
| Edge hotspot | TOPSIS (7/10) | XY (10/10) | XY (10/10) | XY (10/10) |
| Center hotspot | TOPSIS (8/10) | XY (9/10) | XY (10/10) | XY (10/10) |

### Congested port-time: lower is better for this specific metric

| Traffic | 4x4 | 8x8 | 16x16 | 32x32 |
|---|---|---|---|---|
| Uniform | XY (6/10) | XY (8/10) | XY (10/10) | XY (10/10) |
| Transpose | TOPSIS (8/10) | XY (8/10) | XY (9/10) | XY (10/10) |
| Bursty on/off | XY (5/10) | XY (8/10) | XY (9/10) | XY (10/10) |
| Corner hotspot | XY (8/10) | XY (10/10) | XY (10/10) | XY (10/10) |
| Edge hotspot | XY (8/10) | XY (10/10) | XY (10/10) | XY (10/10) |
| Center hotspot | XY (8/10) | XY (10/10) | XY (10/10) | XY (10/10) |

Some remaining light-load points are tied at zero congestion. In particular,
XY's lower congestion in 32x32 corner-hotspot traffic coexists with lower
throughput than the adaptive policies. Read congestion alongside delivered
throughput and completed-packet latency.
