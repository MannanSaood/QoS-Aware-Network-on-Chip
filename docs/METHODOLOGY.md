# Experimental method and limits

## What is implemented

All three route selectors live in separate `algorithms/xy`, `algorithms/dyad`, and
`algorithms/topsis` folders. Both simulator adapters compile those same C++ headers.
The existing SystemVerilog remains a separate hardware artifact. Its
`topsis_arbiter.sv` computes a weighted linear score, not the full normalized
TOPSIS procedure, and arbitrates requests rather than selecting network routes.
The new experiments do not establish that RTL's timing, energy, or correctness.

* **XY:** minimal, X dimension followed by Y.
* **DyAD-OE adaptation:** deterministic selection of the first legal odd-even
  candidate below congestion; least occupied legal candidate when any valid
  neighbor's busiest VC credit occupancy is at least 60%. The deterministic and adaptive
  modes obey the same turn restrictions. Do not replace the first mode with XY:
  the union of XY and odd-even channel dependencies can introduce deadlock.
  Our four-VC credit signal and equal routing-stage latency differ from the
  original paper's FIFO flags and hardware implementation. This is an adaptation,
  not an exact replication of its published results.
* **TOPSIS-OE:** full vector normalization, weighted cost matrix, positive/negative
  ideals, Euclidean distances, and maximum relative closeness. Criteria: aggregate
  credit occupancy (weight 0.7) and maximum per-VC credit occupancy (0.3).
  Ties use the same fixed candidate order. Both criteria use locally available
  credit state, including credit-return delay. Path length is omitted because all
  candidates are minimal; packet age and priority cannot distinguish ports for
  the same packet. This is a project-defined TOPSIS baseline, not a replication of
  a fault-tolerant published algorithm. In NS-2 there are no VCs, so both criteria
  reduce to the same output queue occupancy, explicitly limiting the model.

Odd-even restrictions and strict Manhattan-distance reduction apply regardless
of metric values. Tests exhaustively explore reachable candidates and check the
union channel-dependency graph through 8x8. Random routing trials reach 32x32.
Finite tests supplement the turn-model argument; they are not a formal proof of
the complete simulator, arbitration fairness, protocol deadlock freedom, or RTL.

## Main experiment

The corrected study is specified in [FAIR_COMPARISON_PROTOCOL.md](FAIR_COMPARISON_PROTOCOL.md):
1,944 runs with mesh-aware low-load grids, 5,000 warm-up and 20,000 measured
cycles. `fair_comparison`/`fair_report` use the corrected busiest-VC DyAD trigger.
The earlier aggregate-trigger implementation and its data are archived. The
following primary-grid description documents that older experiment and should
not be attributed to the corrected implementation.

The primary dataset is a **finite-window study**, not a steady-state or SOTA
evaluation: 4x4, 8x8, 16x16 and 32x32 meshes, six traffic cases (uniform,
transpose, bursty, corner/edge/center hotspots), loads 0.1 through 1.0 in steps
of 0.1, seeds 1/2/3 and XY/DyAD-OE/TOPSIS-OE. Its 2160 BookSim runs use
1000 warm-up and 3000 observation cycles and five-flit packets. The validator
requires every combination before exporting the final report. Completed-mesh
previews are explicitly marked partial.

The separate 288-run model/scaling pilot uses both simulators on the same four
mesh sizes, uniform and single-center hotspot;
offered loads 0.05 and 0.3 flits/node/cycle; seeds 1, 2 and 3;
500 warm-up and 1,000 measurement cycles; five-flit packets. This is 288 runs.
Four ordinary subprocess workers run independent cases concurrently; wall times
are diagnostic and affected by contention, not fair engine-speed comparisons.
At saturation,
latency depends strongly on observation duration. Repeat with longer warm-up,
20,000+ measurement cycles and at least ten seeds before making publication claims.

The companion traffic study uses 8x8, loads 0.05/0.1/0.2/0.3/0.4/0.5,
1,000 warm-up and 3,000 observation cycles, three seeds and both simulators.
Its six cases are uniform, transpose, bursty, and three mixed-hotspot locations;
see [REPORT_DESIGN.md](REPORT_DESIGN.md) for exact distributions. This adds 648
runs to the 288-run scaling pilot. The report organizes these into four traffic
sections and uses BookSim as the primary model.

BookSim now ends after writing the fixed-window metrics when `NOC_SKIP_DRAIN`
is set. The earlier implementation drained the network after finalizing those
metrics. Six before/after checks, including all policies on 32x32 hotspot,
matched every network metric exactly (`results/validation/window_finish`). Some
cached pilot runtime values include the old drain, further making them unsuitable
for runtime comparisons. Standard upstream runs without this option still drain.

BookSim uses four VCs, eight flits per VC, iSLIP allocation, non-speculative
operation, one-cycle routing, VC allocation, switch allocation, switch traversal,
and credit delay. All algorithms receive the same modeled routing latency. C++
evaluation time does not automatically become hardware routing delay. `routing_delay`
sensitivity is required to evaluate the cost of TOPSIS arithmetic realistically.
The exact configuration is preserved per run. A pinned upstream checkout and
checked, idempotent source patches keep the experiment reproducible.

NS-2 uses 32 Mbit/s links, 20-byte packets and 1 microsecond link propagation.
One microsecond is an **abstract normalization cycle**, not a proposed chip clock.
Only direct-neighbor forwarding routes are installed using NS-2 manual routing;
the shared algorithm chooses every subsequent hop. Each traversed link takes five cycles of serialization plus one propagation
cycle. The model forwards on packet arrival using actual NS-2 Message agents,
DropTail queues, queue monitors, and scheduled events. It is not a Python
simulation mislabeled as NS-2. Queues have eight packets (40 flit-equivalents),
unlike BookSim's 32-flit input port distributed across VCs. Injection/ejection
interfaces, VC allocation, wormhole backpressure and router pipeline stages are
absent. Local packets bypass physical links. These differences are intentional
model disclosures, not controlled evidence of a particular numerical error.

Within NS-2, a saved arrival file is reused for all algorithms. BookSim uses the
same seed, offered process and settings for each algorithm; its scheduling/RNG
consumption can diverge under backpressure. NS-2 and BookSim use different RNGs,
so the same numeric seed does not mean identical cross-simulator packet traces.
For strict paired cross-simulator studies, add replay of a common injection trace
and specify how source backlog changes the issue time.

Uniform includes self destinations, matching upstream BookSim. Transpose means
(x,y)->(y,x) and therefore includes diagonal self traffic; it is not the
complement/transpose1 pattern in the original DyAD experiment. Upstream BookSim
transpose needs power-of-two mesh sizes. Uniform/hotspot support 3x3 and larger.

### Why hotspot throughput can still overlap after correcting the traffic

Every mixed-hotspot experiment directs probability `p = 0.2 + 0.8/N` to one
destination with one flit/cycle ejection capacity. Serving all offered traffic
at per-node injection `lambda` therefore requires `N * lambda * p <= 1`.
This gives an ideal necessary bound `lambda <= 1/(0.2*N + 0.8)`:

| Mesh | Routers N | Ideal per-node offered-rate bound (flits/node/cycle) |
|---|---:|---:|
| 4x4 | 16 | 0.250000 |
| 8x8 | 64 | 0.073529 |
| 16x16 | 256 | 0.019231 |
| 32x32 | 1024 | 0.004864 |

Routing may encounter additional bottlenecks before this bound. It cannot
increase the single destination's ejection bandwidth. Thus the requested
0.1–1.0 sweep intentionally includes overload, and all mixed-hotspot points
on meshes 8x8 and larger exceed this necessary bound. Similar throughput
under those conditions is plausible even with different route choices.
Completed-packet selection and finite observation windows mean this bound
must not be used to clip measured throughput or manufacture equality.
Study the curves as overload behavior, not steady-state tail-latency estimates.
The corrected `fair_comparison` follow-up supplies finer points below and around
these bounds to examine lightly loaded hotspot behavior and its transition.

## CSV metric definitions

| Field | Definition and interpretation |
|---|---|
| `latency_p50_cycles`, `latency_p90_cycles`, `latency_p99_cycles` | Median, 90th and 99th percentile creation-to-completion latency of packets **arriving in the observation window**, including source queueing in BookSim. Nearest-rank percentiles. Mean and p95 are also retained. In-flight packets are censored, so latency alone can reward a saturated network; read alongside throughput. |
| `throughput_flits_per_node_cycle` | Completed packets x packet flits / (nodes x measurement cycles). A packet-based rate; differs slightly from accepted flit rate at window boundaries. |
| `throughput_offered_pct` | Throughput / configured offered flit rate x 100. A traffic-service ratio, not power/area efficiency or a cohort delivery probability. Finite-window randomness can make it slightly exceed 100%; do not clamp it. |
| `buffer_occupancy_pct` | Mean occupancy/capacity sampled every 10 cycles over valid directed inter-router ports. BookSim input buffers; NS-2 output queues excluding the packet in service. These are different observables. |
| `congested_port_time_pct` | Percentage of valid port samples at occupancy >=60%, sampled every 10 cycles. This is not percentage of packets lost. |
| `link_utilization_pct` | BookSim physical inter-router flit traversals / (directed links x cycles). NS-2 serialization busy time intersected with the observation window. Boundary dummy links are excluded. |
| `peak_link_utilization_pct` | Maximum utilization of any one physical directed link. |
| `mean_hops` | Completed packets' inter-router Manhattan hops; local delivery is zero. BookSim's extra destination-router count is subtracted. |
| `wall_seconds` | Measured subprocess runtime including startup; NS-2 and earlier cached BookSim rows also include drain. Excludes CSV parsing/plotting. Host load and instrumentation affect it. Diagnostic only, not silicon latency or algorithm-only complexity. |
| `drops` | NS-2 DropTail events during the measurement window; zero for BookSim's lossless credit model. Source backlog is not loss. |
| `cohort_delivery_pct` | NS-2 packets born in the window that finish by the drain limit / window births. Missing for BookSim; never silently fill missing results with zero. |

All successful rows also carry engine, algorithm, mesh, traffic, load, seed, packet
size, warm-up and measurement duration. The manifest records source hashes and
the pinned BookSim revision. Logs, configs, arrival files, packet completions and
compressed NS-2 traces retain provenance. A failed or timed-out run remains a
failed row and does not produce invented metric values. Re-running into the same
directory overwrites matching run names; use a new directory for changed studies.

Plots show means and two-sided 95% Student-t intervals **across independent seeds**.
For a percentile metric the interval describes the between-run mean percentile,
not a confidence interval estimated from every packet. Three seeds yield broad,
fragile intervals. Do not infer significance from curve ordering alone. Both
engines are plotted separately; no spurious universal accuracy score is computed.

## What can establish higher NoC fidelity

BookSim is explicitly a cycle-accurate interconnection-network simulator
([official source](https://github.com/booksim/booksim2)); NS-2 is a general
networking discrete-event simulator ([official overview](https://www.isi.edu/websites/nsnam/ns/)).
Their suitability follows from the modeled mechanisms, not whether they are
commercial or used in industry.

1. Check an isolated NS-2 h-hop packet against h(P+1) normalized cycles. Increasing
   packet length adds h cycles per extra flit in this store-and-forward model.
2. Check BookSim no-contention latency against its configured pipeline and flit
   serialization, then sweep packet size, credit delay, VC count and buffer depth.
   Wormhole pipelining has different serialization scaling from store-and-forward.
3. Check the all-to-one bottleneck: with a one-flit/cycle destination ejection port,
   aggregate sustained throughput is at most one flit/cycle. This NS-2 abstraction
   has no shared destination ejection server, so multiple ingress links can deliver
   simultaneously. That is a concrete missing NoC constraint, not an NS-2 defect.
4. Validate both against an independent cycle-level RTL trace or measured target
   architecture before claiming numerical accuracy. No Vivado is needed for these
   simulations; an open-source RTL tool could provide a future reference.

The defensible conclusion is “BookSim captures more of the target NoC mechanisms
than this NS-2 packet abstraction.” “NS-2 is bad” or “BookSim is X% more accurate”
does not follow from the current evidence.
