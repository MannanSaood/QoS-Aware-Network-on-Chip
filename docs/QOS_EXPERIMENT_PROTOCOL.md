# QoS experiment specification

Status: specified before measurement on 14 October 2026; implemented and directed
validation passed. Full performance sweep in progress; results are not yet final.
This is a soft differentiated-service testbed for existing routing algorithms,
not the proposed new hybrid algorithm and not a reproduction of Yu et al.

## Required behavior

1. Replay one immutable packet-demand trace for every algorithm and scheduling
   mode in a scenario. Events contain creation cycle, source, destination and
   class. Generate the trace independently of routing and backpressure.
2. Two classes: critical (class 0, expected 25% of packets) and best effort
   (class 1, expected 75%). Assignment is independent of source/destination.
   Total offered load is the sum of both classes, not a per-class multiplier.
3. Maintain four VCs of eight flits per input: VCs 0–1 critical, 2–3 best effort.
   Both modes use this same partition; do not compare their absolute results
   directly to the old unpartitioned one-class run as a pure QoS effect.
4. Use priority-aware separable output-first VC and switch allocation, with
   round-robin tie resolution, no speculative allocation or packet switch hold.
   Apply packet priority at source injection and throughout its route.
   BookSim `priority=class` enables VC propagation of the explicit replay priority;
   the extension sets the actual class/age value. `priority=none` is rejected.
5. Control: oldest creation time first without class preference. Showcase QoS:
   weighted 3:1 critical/best-effort service at the source and local arbiters,
   oldest creation time first within each class. State advances on accepted
   grants; an idle preferred class permits the other class to borrow service.
   Input-request coalescing consults the same output schedule, so it cannot
   silently eliminate a waiting best-effort request before weighted arbitration.
   This revises the original strict-priority FR3 following the user's direction
   to select a policy suited to mixed real-world workloads. Local 3:1 arbitration
   is not a guaranteed end-to-end bandwidth ratio: credits, routing and matching
   constrain eligibility. Strict priority and an optional age-biased policy
   remain explicit test modes; neither is the showcase treatment.
6. Preserve XY, corrected DyAD-OE and project TOPSIS-OE route selection. A class
   cannot change its VC partition. All policies observe the same total credit
   pressure. Routing delay remains one cycle, explicitly a modeling assumption.
7. Record each offered packet, head injection and tail delivery. Check packet
   conservation, destination/class integrity, allowed VC use and window counts.
8. Critical relative deadline: 16*k cycles from demand creation. This is a
   predeclared synthetic service target, not an application-derived deadline or
   guarantee. Count a deadline outcome only when its deadline has elapsed by
   the final observed cycle. Count pending eligible packets as misses, and
   report later-deadline packets separately as censored.

## Measurement and test matrix

Use 5,000 warm-up and 20,000 observation cycles; 5-flit packets. Preserve source
queueing in latency. Report generated, injected, delivered, pending-at-source,
pending-in-network, oldest pending age, and time-window throughput by class.
Report p50/p90/p99 for completed packets by class, together with missing/censored
demand. Separate actual ejected-flit throughput from completed-packet-equivalent
flit throughput. Collect half-window tails/delivery counts and physical-port
congestion using the same definition as the existing study.

Main scenarios: 4x4, 8x8, 16x16 and 32x32; uniform, transpose, bursty and three
fixed hotspot locations. Independent seeds 1, 2 and 3. For non-hotspot traffic,
sample load `(4/k) * [0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0]`.
For hotspot traffic sample
`[0.1, 0.25, 0.5, 0.7, 0.85, 1.0, 1.15, 1.5, 2.0] / (0.2*k*k + 0.8)`. These are capacity-reference
sampling scales, not predictions of saturation. All loads are flits/node/cycle.
The expected matrix contains 3,888 simulations: 4 meshes * 6 cases * 9 loads *
3 seeds * 3 algorithms * 2 scheduling modes.

Uniform permits self traffic, transpose swaps coordinates, bursty has symmetric
on/off transition probability 0.02 and twice the mean injection probability
while on. Hotspot destination is a 20% fixed target / 80% uniform mixture, using
corner 0, edge k/2, or center (k/2)*k+k/2. A hotspot location stays fixed within
each run. Migration and application traces are later experiments.

Validate controlled single-packet latency, competing class requests, optional
priority aging, no-load invariance, replay identity, conservation, deadline boundary
handling and VC isolation before the matrix. An integration test must show a
priority change can change an actual BookSim arbitration outcome, not merely
the stored label. Repeated runs must reproduce exact deterministic metrics.

Summaries use seed-level confidence intervals and paired treatment/control
deltas. They must preserve regressions and near ties. Inspect pending growth
before interpreting a lower completed-packet p99 as an improvement. Per-source
fairness uses comparable within-class demand; aggregate class share equality is
not an objective when service is intentionally differentiated.

## Isolation and remaining limits

Build this extension in `.deps/booksim2_qos`; never rebuild or patch the binary
used by the running frozen single-class sweep. Store QoS-specific adapter source
in `simulators/booksim_qos` and results in their own directory. Record original
and new source/binary hashes and complete experiment parameters.

No fault, energy, area, hard real-time guarantee or SOTA claim is established by
these experiments. Paper reproduction remains in the sibling repository. The
new hybrid routing algorithm is explicitly deferred to the next user prompt.
