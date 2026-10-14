# Evaluation framework readiness audit

Audit date: 14 October 2026. Scope: pinned BookSim2 source and this project's
adapter/configurations, not the separately validated original RTL.

Status update: the two-class QoS extension described later in this audit is now
implemented and directed validation has passed. Its 4×4, 8×8 and 16×16 sweeps
are complete; 32×32 is running. The gap table below records the earlier
single-class baseline, not the current QoS implementation. See
[project status](PROJECT_STATUS.md) and [QoS protocol](QOS_EXPERIMENT_PROTOCOL.md).

## What already exists

BookSim already implements traffic generation, source queues, finite input VCs,
credit flow control, VC allocation, switch allocation, links and packet retirement.
See `.deps/booksim2/doc/manual.tex` (input-queued router, allocators, traffic and
simulation sections), `src/trafficmanager.cpp`, `src/vc.cpp` and
`src/routers/iq_router.cpp`. These components are not absent from our simulation.
The earlier single-class experiment measures three routing policies under a
common microarchitecture and is now paused.

## Earlier single-class gaps and research limitations

| Component | Earlier single-class baseline | Addition / limitation (implementation status below) |
|---|---|---|
| Service classes | Adapter requires exactly one class | Two explicitly defined classes, source classification and class-preserving VCs |
| Packet priority | Default `priority=none` | An implemented policy consumed at injection, VC allocation and switch allocation |
| Priority arbitration | iSLIP grants scan round-robin without using request priorities | A priority-aware allocator for both treatment and matched control; test competing requests |
| Repeatable demand | Matched native RNG seeds; routing timing can change draw order | Replay identical timestamp/source/destination/class demand for every policy |
| Source backlog | Implicit native generation queue; completed-packet metrics only | Explicit offered/generated, injected, delivered and pending counts, conservation checks |
| QoS metrics | Aggregate percentiles and throughput | Per-class percentiles/throughput, eligible deadline outcomes including undelivered packets, pending age |
| Congestion resolution | Physical-port occupancy aggregated over all VCs | Current QoS build adds per-class backlog, but not per-class occupancy samples; aggregate pressure can hide a full class-specific VC pool |
| Fairness | No demand-normalized per-source result | Per-class delivery fraction by source and within-class fairness; distinguish equal shares from unequal demand |
| Observation boundary | Fixed window; completed arrivals can exclude stuck packets | Pair tails with backlog/drift and deadline censoring; do not call overloaded finite-window latency steady-state |
| Routing cost | All policies use one routing cycle | Later measured/sensitivity-tested decision delay, control traffic, area and energy; no hardware-efficiency claim yet |
| Fault tolerance | Fault-free minimal routes | Separate fault models, reachability and fault-aware deadlock/livelock design before fault claims |
| Application realism | Six synthetic cases | Later application traces, migration and held-out mixtures; transpose is a spatial permutation, not on/off traffic |
| Statistical power | Three seeds, confidence intervals | More repetitions where intervals are broad; predeclare an equivalence margin before calling outcomes equal |

The manual lists `separable_input_first` and `separable_output_first` allocators.
In source, `separable_input_first.cpp` forwards `in_pri`/`out_pri` to arbiters;
`roundrobin_arb.cpp` compares priorities before resolving ties. Merely changing
the traffic manager's class label while retaining the old iSLIP grant logic
would not provide the intended end-to-end priority policy.

## Implemented QoS experiment scope

Soft differentiated service is implemented in the main repository using an
isolated BookSim build, preserving the earlier study's binary and source hashes.
The age-only control and QoS treatment use the same traffic trace, class split,
VC partition, allocator and resources. Only the class service policy changes
between these modes. Both exercise XY, DyAD-OE (adapted) and TOPSIS-OE (project).

The implemented treatment uses 3:1 class-weighted service with oldest-first
ordering within each class; the control uses oldest-first without class preference.
Weighted local grants allow best-effort service under contention. This is not a
hard deadline guarantee, admission controller or proven bandwidth reservation.
Do not claim the network is universally work-conserving merely because priority
arbitration is used: finite separable matching and downstream credits constrain
eligible transfers. Controlled arbitration and starvation checks are required.

The paper-specific environment and any adaptations belong in the sibling
`Paper-TOPSIS-Reproduction` repository. Adding application QoS here does not
resolve the missing original Noxim implementation or make the project TOPSIS
selector equivalent to the paper's released selector.

## Implemented and checked on 14 October 2026

The isolated `booksim2_qos` build now has external demand replay, class-preserving
VC pools, weighted/age/strict/age-biased arbitration modes, per-class tails,
source/network backlog, synthetic deadline outcomes and demand-normalized fairness.
`scripts/validate_qos.py` checks 10,240 XY packets spanning every 4x4 source/destination
pair, depth-4 buffers, all three selectors, payload/VC identity, exact repeat runs,
deadline accounting against an independent event-log calculation, and actual router
service differentiation. The two-input saturation test delivers about 77% of
ejected flits to critical traffic versus about 50% under the control. Eligibility
and credits explain why an observed end-to-end share need not be exactly 75%.

Validation caught and corrected a configuration defect before the sweep:
`priority=none` prevented BookSim VCs from forwarding packet priority to router
arbiters. The build now rejects that configuration. Use `priority=class` to carry
the explicitly assigned replay priority. Policy unit tests alone did not detect
this integration issue; the contended-router test is retained as a regression check.

This implements and validates the simulator-level FR1/FR2 behavior and the revised
weighted FR3 policy. It does not revalidate the original RTL, prove hard deadlines,
or establish the original strict-priority 30% latency-improvement performance target.
The showcase sweep is separate evidence and must complete before performance claims.

The replay adapter is scoped to the configured synthetic, one-way throughput
experiment (`use_read_write=0`, the pinned default; `priority=class`). It bypasses
native `_IssuePacket`, so native request-outstanding and packet-sequence counters
are not maintained by replay. Source inspection confirms those counters do not
control this experiment's routes, grants or exported measurements; the explicit
replay packet tracker supplies conservation/backlog data. Batch traffic, memory
request/reply traffic and sequence-based priority need integration work before
they can be advertised as supported. Do not apply this adapter to those modes
without updating the bookkeeping and validating their semantics.
