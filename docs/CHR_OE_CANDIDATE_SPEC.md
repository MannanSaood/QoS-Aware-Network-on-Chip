# CHR-OE: candidate specification (Gate 0)

**Status: specification only. Nothing here is implemented, simulated or measured.**
Drafted 7 November 2026 on branch `codex/hybrid-routing-research`. Every
performance statement below is a hypothesis or a proposed acceptance rule, unless
it cites a frozen measurement explicitly.

CHR-OE = **C**lass-aware **H**ysteretic **R**outing on the **O**dd-**E**ven legal set.
It is "Candidate A" from `HYBRID_RESEARCH_PLAN.md`: every decision chooses
from the existing, already-tested `noc::odd_even()` candidate set.

---

## 1. What problem this candidate targets

These are frozen weighted-service measurements, three-seed means from
`results/qos_report/summary.csv` at each scenario's highest sampled load:

| Scenario | Metric | XY | DyAD-OE | TOPSIS-OE |
|---|---|---:|---:|---:|
| 8×8 uniform, 0.5 | total throughput | 0.2963 | 0.2302 | 0.2316 |
| 32×32 uniform, 0.125 | total throughput | 0.0781 | 0.0448 | 0.0439 |
| 8×8 transpose, 0.5 | critical p99 (cycles) | 3084.7 | 95.7 | 96.3 |
| 32×32 transpose, 0.125 | critical p99 (cycles) | 4704 | 8902 | 8456 |

The two project adaptive selectors win clearly on 8×8 and 16×16 transpose.
They lose a large share of uniform-traffic throughput, and the loss grows with
mesh size. **The target is that uniform-traffic loss, without giving up the
transpose gain.**

### 1.1 What the code already tells us (fact, from reading the source)

- `odd_even()` returns its candidates in a fixed order. DyAD-OE's uncongested mode
  takes `ports[0]`. For westbound packets (`dx<0`) `ports[0]` is always `W`. For
  eastbound packets it is `E`, except when `dx==1`, `dy!=0` and the destination
  column is even. In that case `E` is not legal, so the packet moves vertically
  first and takes its final east hop last. Pure-vertical and pure-horizontal
  packets are routed exactly as XY routes them.
- So **"always take `ports[0]`" (called OE-fixed below) differs from XY only on
  the last column of some eastbound routes.** A Python port of `odd_even()`
  walked every source–destination pair. It found no deviation outside that
  case. Whole paths differ from XY for 24/256 pairs at k=4, 672/4096 at k=8
  and 13,440/65,536 (20.5%) at k=16. This is a path-set check, not a
  performance measurement.
- DyAD-OE switches to adaptive mode when the **peak single-VC occupancy of any
  valid neighbour port is ≥ 0.6**. That peak covers all four VCs of both
  classes, including ports the packet cannot use. Once triggered, it picks the
  legal port with the lowest *total* (both-class) occupancy. The mode has no
  memory, so it is re-evaluated from scratch at every head flit.
- The production config uses `wait_for_tail_credit = 1` with two VCs per class.
  A downstream class VC therefore stays unavailable until its tail credit
  returns, even if its buffer is nearly empty. The routing adapter only sees
  credit occupancy, so it cannot see whether a VC is free.

### 1.2 Hypotheses (not established; the pilot is designed to test them)

- **H1:** OE-fixed delivers about the same uniform throughput as XY (within 3%),
  so the OE turn restriction is *not* the main cause of the uniform loss.
- **H2:** Most of the uniform loss comes from the adaptive mode itself. Under
  uniform load near the cut capacity, the any-port, any-class trigger is almost
  always on, so the router keeps making greedy, memoryless local choices. Those
  choices either spread traffic onto worse paths or herd it.
- **H3:** A trigger that (a) looks only at the packet's own class, (b) looks only
  at the default port, (c) has temporal hysteresis, and (d) leaves the default
  only when the alternative is better by a margin will adapt rarely under
  uniform traffic and often under transpose concentration.

**H1 is a go/no-go test for this whole candidate (§7, D0).** If OE-fixed loses
more than 3% throughput to XY on uniform traffic at k ≥ 16, then no OE-only
selector can meet the uniform target. In that case CHR-OE is set aside and the
study moves to Candidate B: west-first with an exact XY default.

---

## 2. Legality and safety architecture

- **Legal set:** `L = noc::odd_even(src, cur, dst, k)`, unchanged, in every mode.
  CHR-OE never emits a port outside `L`. The fixed candidate order is the
  default order.
- **VC set:** the packet's own class range `[c·V/2, (c+1)·V/2 − 1]`, as the
  QoS build patches it today. There is no escape VC, no class migration and no
  change to the injection VC range.
- **Minimal, fault-free routing only.** Detours and faults are out of scope.
- **Deadlock argument (to be written up in full and checked, not assumed):**
  1. Within one class, every hop uses a minimal odd-even turn. The odd-even turn
     model forbids the turn pairs needed to close a cycle (Chiu, IEEE TPDS 2000).
     Its channel-dependency graph over physical channels is acyclic for minimal
     routing, whatever selection function picks among the legal ports. The
     source-column lookahead rule in `odd_even()` is part of the verified
     candidate generator and stays as it is.
  2. Every VC a class can use lies on a physical channel in that acyclic graph.
     The VC-level dependency graph maps onto it, so it is acyclic too.
  3. The classes share only the crossbar and links. With
     `hold_switch_for_packet = 0`, neither is held across cycles. The weighted
     arbiter is work-conserving: an idle preferred class lends its slot. While
     both classes are eligible, best effort gets 1 of every 4 accepted grants,
     so it cannot be starved indefinitely.
  4. **Gate 1 checks:** generate the channel-dependency graph mechanically from
     the implemented route function over every (src, cur, dst) triple for
     k ∈ {4, 5, 6, 8} and check it for cycles. Then run saturation stress tests
     and check that every run drains completely. Neither the simulations nor this
     sketch is a formal proof. The write-up must say so.
- **Livelock:** every hop strictly reduces Manhattan distance. This covers
  livelock only, not deadlock.

---

## 3. Decision rule

Notation for a head flit of class `c` at router `r`, with legal set
`L = [p0]` or `[p0, p1]` (`p0` is the default):

- `u[c][p]`: class-local downstream occupancy of output `p`, meaning the summed
  used credits over class `c`'s VCs, scaled to 0–15 (4 bits) against the
  **reachable** class capacity `VCs_per_class × min(depth, packet flits)`
  (10 flits in production). See amendment A1 in §10. The router already
  keeps this in its per-VC credit counters, so no new inter-router wires are
  needed.
- `e[c][p]`: a per-router, per-class, per-output filtered pressure register
  (6-bit register, steady-state range 0–60), updated every cycle from `u[c][p]`:
  `e ← e + (((u<<2) − e) >> 2)`, i.e. an EWMA with α = 1/4. It uses an
  arithmetic shift, and its behaviour on rounding and negative steps is fixed by
  unit tests.
  The route stage reads the value registered at the end of the previous cycle.
- `h[c][p]`: a hysteresis bit. It sets when `e ≥ T_on` and clears when
  `e ≤ T_off`.
- `f[c][p]`: number of free (unallocated) class-`c` VCs at downstream output `p`
  (0–2). This needs a new read-only router accessor in the CHR build. It is
  ablated separately (§6) because it is a new signal.

```text
route(c, L):
  if |L| == 1:            return L[0]                 # bypass, no state read
  p0, p1 = L
  if h[c][p0] == 0:       return p0                   # default port not pressured
  # default is pressured: compare (lower is better)
  cost(p) = (f[c][p] == 0 ? F_PEN : 0) + (e[c][p] >> 2)   # 4-bit e plus penalty, integers only
  if cost(p1) + M <= cost(p0): return p1              # switch only by margin M
  return p0                                            # ties and small gains stay on default
```

There is no square root, no division, no floating point and no dynamic
container. Per decision the datapath is two 5-bit adds, one 5-bit compare, one
hysteresis-bit read and a 2-way mux. **Whether this fits a one-cycle route stage
is an assumption until synthesized (Gate 5).**

### 3.1 Starting parameters (fixed before tuning; tuned on the tuning set only)

| Name | Start | Meaning |
|---|---:|---|
| α | 1/4 | EWMA weight (shift by 2) |
| `T_on` | 38 on the 0–60 `e` scale (≈ 0.63 of full) | Enter pressured state |
| `T_off` | 23 (≈ 0.38) | Leave pressured state |
| `M` | 2 (of 15) | Switching margin, biased towards the default |
| `F_PEN` | 4 | Penalty when no class VC is free downstream |

Tuning may change only these five values, and only within the ranges
α ∈ {1/2, 1/4, 1/8}, `T_on` ∈ [0.5, 0.8], `T_off` ∈ [0.2, `T_on` − 0.1],
`M` ∈ {0..4} and `F_PEN` ∈ {0, 2, 4, 8}. The chosen values are frozen and
hashed before any held-out run.

### 3.2 Storage and control cost (estimate to be checked)

- State: 2 classes × 4 outputs × (6-bit `e` + 1-bit `h`) = **56 bits per router**.
- Inter-router control traffic: **none**. All inputs are local credit and
  VC-allocation state that a credit-based router already keeps.
- Per-cycle update logic: 8 shift-subtract-add EWMA updates and 8 threshold
  compares. This logic is outside the route critical path but costs energy every
  cycle. A clock-gated, event-driven update is a possible later refinement.
- **Not claimed:** area, energy or timing. These need synthesis of the datapath
  under declared constraints (Gate 5).

### 3.3 What is and is not new (honest prior-art position)

- Class-aware adaptive routing, hysteresis/dual thresholds, deterministic
  defaults with adaptive fallback (DyAD, DAHR, PcaDAHR) and credit-based local
  selection are all prior art.
- The working contribution, *if the evidence supports it*, is narrower: a
  **default-biased, class-local, hysteretic selector on a fixed legal set, with
  no added control wires**. The claim would be that it retains XY-like uniform
  throughput while keeping most of the adaptive transpose benefit at 56 bits of
  state per router. A full-text check against DAHR, PcaDAHR and RCA is required
  before calling any part of this novel.

---

## 4. Implementation plan and isolation rules

Nothing under `results/qos_comparison`, `results/qos_report`,
`.deps/booksim2_qos` or `W\output` is modified.

| Item | Location (new) |
|---|---|
| Selector | `algorithms/chr/routing.hpp` (pure function plus a small state struct, no BookSim types) |
| Ablation flags | Compile-time parameter struct; each ablation is a named route (`noc_chr_*`) |
| OE-fixed control | `algorithms/oefixed/routing.hpp` (always `ports[0]`) |
| BookSim build | `.deps/booksim2_chr` via a new `scripts/setup_chr.py` that applies the existing QoS patches plus the CHR routes, a per-cycle EWMA hook and a free-VC accessor |
| Instrumentation | Compiled in, switched on by an environment variable, writes a separate JSON |
| Runner | New `scripts/run_chr_study.py`. `run_qos_grid.py` hardcodes its output directory, algorithm list and expected run count, so it is left unchanged. |
| Results | `results/chr_study/<stage>/` with its own `protocol.json`, binary hash and progress receipt |

**Regression gate before any CHR measurement (R0):** the CHR build must
reproduce the frozen `result.json` metrics **exactly** for XY, DyAD-OE and
TOPSIS-OE in both modes on at least 12 frozen cases (k = 4 and 8, all six
traffics, seed 1, two loads). Only if R0 passes may new CHR runs be compared
with the frozen seed 1–3 baselines. If R0 fails, every baseline is re-run under
the new binary for every comparison, and the frozen numbers are not mixed in.

---

## 5. Instrumentation (CHR build only)

Each counter must first be checked against a hand-computed example on a 2×2 or
3×3 mesh. Only then may it be interpreted.

- Decisions: count with `|L| = 1`, count with `|L| = 2`, how many chose the
  default, how many switched, and how often the default was pressured but kept
  because of the margin.
- Per (class, output): hysteresis-on time fraction and number of transitions
  (to detect oscillation).
- Per (class, output): VC-allocation requests, grants, cycles stalled with no
  free class VC, and switch grants by class.
- Head-of-line age at route time, and source-queue waiting versus fabric waiting
  per class.
- Link utilization map at the end of the window. This tests the transpose
  bottleneck-link prediction `λ ≤ 1/(k−1)`.

---

## 6. Ablations (same build, same traces)

| Route | Default | Trigger | Comparison | Purpose |
|---|---|---|---|---|
| `xy` | — | — | — | Baseline |
| `oefixed` | `p0` | never | — | **D0**: isolates the cost of the OE turn restriction |
| `dyad` | `p0` | any-port, any-class peak ≥ 0.6 | min total occupancy | Frozen comparator |
| `topsis` | — | always | TOPSIS | Frozen comparator |
| `chr_cls` | `p0` | DyAD rule but class-local and on `p0` only, no filter or hysteresis | min class-local occupancy | Effect of class-local signal only |
| `chr_hyst` | `p0` | `chr_cls` plus EWMA and hysteresis | min class-local occupancy | Adds temporal filtering |
| `chr_nofv` | `p0` | full | full, but `F_PEN = 0` | Value of the free-VC signal |
| `chr` | `p0` | full | full | Candidate |

A plain adaptive west-first comparator is not needed for Candidate A. It
becomes mandatory if D0 triggers the switch to Candidate B.

---

## 7. Staged gates for this candidate

**G1, correctness (no performance runs before this passes):**
- Exhaustive unit tests: for every (src, cur, dst) on k ∈ {3, 4, 5, 8} and every
  quantized state combination of two candidates, the output is in `L` and the
  route reaches `dst` in exactly Manhattan-distance hops.
- A mechanical channel-dependency-graph cycle check, as described in §2.
- Integrity: the existing QoS checks hold (VC partition, payload tags,
  conservation, no duplicate retirement) with zero integrity errors.
- Determinism: identical trace plus identical binary gives byte-identical
  metrics.
- The R0 regression gate (§4).

**G2, directed micro-pilots (minutes, not hours):**
1. A single packet on an empty network: same latency as `oefixed`.
2. Synthetic credit imbalance on the default port (tiny scripted case): switches
   only once `e` crosses `T_on`, then stays switched until it drops below `T_off`.
3. Two classes sharing a congested output: the critical-class trigger must not
   fire on best-effort-only pressure.
4. A short burst: check the transition count to confirm the hysteresis prevents
   oscillation.
5. Hotspot spillover onto unrelated flows (diagnostic only).

**D0 + G3, tuning pilot** (weighted mode only; all routes from §6):
- Meshes k = 8 and 16. Traffic: uniform, transpose and hotspot_center. Five
  loads per traffic spanning the transition region, taken from the frozen load
  grids. **New trace seeds 101, 102, 103**, generated fresh, so tuning never
  touches the seed 1–3 showcase traces.
- Stage 3a (k = 8) has 3 × 5 × 3 × 8 = 360 runs. Stage 3b (k = 16) is the same
  size. Wall-clock time is estimated from frozen per-case durations before
  launch.
- **D0 decision rule (fixed now):** if `oefixed` mean uniform throughput falls
  below XY by more than 3% (relative) at any of the top three uniform loads at
  k = 16, stop CHR-OE and write the Candidate B spec.
- Parameter tuning is limited to the §3.1 ranges. All tried configurations are
  logged, including rejected ones.

**G4, held-out evaluation** (only after the parameters are frozen and hashed):
- Four meshes (k = 4, 8, 16, 32), all six frozen traffic cases on their frozen
  load grids, **seeds 201–205** (5 seeds), both scheduling modes (age and
  weighted), routes `xy`, `dyad`, `topsis`, `oefixed`, `chr`.
- The seed 1–3 showcase traces are re-run for continuity only and labelled
  *not held out*, because they were seen during design.
- Additional unseen traffic (e.g. bit-complement, shuffle, longer/shorter bursts,
  migrating hotspot) is added only after each generator is implemented and
  validated separately.
- 64×64 is considered only after G4 at k = 32 meets the criteria in §8.

**G5, cost:** synthesize the selector datapath plus the EWMA update and report
area, critical path and per-cycle energy under declared constraints. Run a
sensitivity check with `routing_delay = 2` for every route on a subset.

---

## 8. Acceptance criteria (agreed 7 November 2026, see §9)

The paired unit is the seed (same trace across routes). "Lower bound" means the
lower 95% confidence bound of the paired difference across five seeds. All
margins are fixed now, before any data.

1. **Uniform noninferiority vs XY** (weighted mode, every load where XY's
   critical pending growth is ≤ 1% of generated critical packets, all four
   meshes):
   - Total throughput: lower bound of (CHR − XY)/XY > −3%.
   - Critical p99: upper bound of (CHR − XY) < max(10% of XY, 5 cycles).
   - Best-effort p99: upper bound < max(10% of XY, 10 cycles).
2. **Transpose:** at k = 8 and 16, at loads where XY's critical misses exceed
   5%, CHR critical deadline misses are within 1 percentage point of the better
   of DyAD-OE and TOPSIS-OE, *and* total throughput is no more than 3% below it.
   At k = 32 every metric is reported, with no pass/fail target, because the
   frozen baselines reverse there.
3. **Hotspots and bursty:** no metric worse than XY by more than the uniform
   margins, unless it is shown to be the sink-capacity limit
   (`λ ≤ 1/(0.2k² + 0.8)`) that no routing policy can exceed.
4. **No hidden costs:** pending demand, oldest-pending age and best-effort
   delivery fraction are reported next to every p99, and any regression there
   is reported as a regression.
5. **Cost:** ≤ 64 bits of state per router, zero added inter-router control
   bits, and a route stage modelled at 1 cycle pending G5. If G5 shows it does
   not fit, the `routing_delay = 2` results become the primary ones.
6. **Safety:** zero integrity errors, no cycles in the channel-dependency check,
   and every stress run drains.

**If CHR-OE fails a criterion,** the failure is reported as such. The thresholds
are not loosened after the data is seen, and the mechanism is diagnosed with the
§5 counters. A documented negative result is an acceptable outcome.

---

## 9. Decisions recorded (user, 7 November 2026)

1. **Margins:** the §8 margins are fixed as written, before any evaluation run.
   They are not changed after tuning or held-out data is seen. §8 is therefore
   **agreed**, not merely proposed.
2. **Free-VC accessor:** approved for the new CHR build only. The frozen build
   is not modified.
3. **Scheduling modes in G4:** the more accurate option is chosen. Every G4
   route runs in **both** age-only and weighted modes on the full matrix. The
   matched control is then available for every scenario, so routing gains and
   scheduling gains can be told apart everywhere, not only on a subset.

---

## 10. Amendments (dated; made before any tuning or evaluation run)

**A1, 7 November 2026: normalization against reachable capacity (G1 finding).**
The first draft scaled class occupancy against the raw buffer capacity
(2 VCs × 8 flits = 16). The production config uses `wait_for_tail_credit = 1`,
so a VC holds flits of at most one 5-flit packet. Class occupancy therefore
peaks at 10 of 16, which caps `u` at 9 and `e` at 36. That is below
`T_on = 38`, so the trigger could never fire. The first smoke run showed it:
`chr`, `chr_hyst` and `chr_nofv` produced results identical to `oefixed`, with
0% hysteresis-on time, on a 4×4 transpose trace at load 0.8. The fix
normalizes against the reachable capacity, `VCs_per_class × min(depth,
packet flits)`. The CHR build now refuses to run unless
`wait_for_tail_credit = 1`, because the capacity model depends on it.
The threshold fractions (≈0.63 on, ≈0.38 off), the tuning ranges and the §8
acceptance criteria are unchanged. A related observation, not a change: the
frozen DyAD-OE trigger (`peak/depth ≥ 0.6`) can only fire when one downstream VC
holds a complete 5-flit packet (5/8 = 0.625).

---

## 11. Pilot result, stage 3a (8×8), 7 November 2026

Weighted mode, starting parameters (A1), fresh seeds 101–103, 360 runs. There
were zero integrity errors and all three determinism repeats were identical.
Full tables: `results/chr_study/pilot_k8/SUMMARY.md`; paired intervals:
`paired.csv` (t-intervals over 3 seeds, exploratory, not multiplicity-adjusted).

**H1 is falsified.** OE-fixed loses about a third of XY's uniform throughput,
even though its paths differ from XY for only 16% of pairs:

| Uniform load | OE-fixed vs XY throughput | DyAD-OE vs OE-fixed | CHR vs XY |
|---:|---:|---:|---:|
| 0.3 | −33.3% [−34.1, −32.5] | +13.5% [+11.7, +15.3] | −30.6% [−32.6, −28.6] |
| 0.4 | −32.2% [−34.3, −30.2] | +12.0% [+8.6, +15.3] | −28.4% [−32.3, −24.4] |
| 0.5 | −31.1% [−34.9, −27.3] | +14.6% [+8.0, +21.3] | −25.6% [−28.2, −23.0] |

So H2 is also wrong as stated. The project adaptive selectors' uniform loss
comes mainly from the **odd-even path structure itself**: adaptivity recovers
part of the loss rather than causing it. An OE-only default cannot meet the
uniform target. The formal D0 rule names k = 16, but the k = 8 gap is about
10 times the 3% margin.

**Transpose:** CHR's default-biased design adapts too reluctantly. At
load 0.5, CHR's critical p99 is 162 cycles against 97 for DyAD-OE
(+67% [+52, +83]), with 5.3% critical misses against 0%. It still beats XY's
3060 cycles by a wide margin. `chr_hyst` (no margin, no free-VC penalty) is the
best CHR variant, about 2% below DyAD-OE in throughput. The margin and the
free-VC penalty did not help.

**Hotspot (center):** every route plateaus near 0.067 flits/node/cycle,
about 91% of the sink bound `1/13.6 = 0.0735`. Critical p99 stays at 71 cycles
for every route. Differences are within noise, which is consistent with a
sink limit that routing cannot remove.

**Decision:** CHR-OE is closed as a candidate. It is a measured negative
result and is kept as a comparator. The k = 16 stage 3b is not run for it.
The findings feed SAQR directly: an exact XY default (no odd-even structure),
readier adaptation (margin 0, no free-VC penalty as defaults to ablate), and
no expectation of hotspot gains beyond protecting other traffic.
