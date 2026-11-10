# SAQR: Safe Adaptive QoS Routing (spec v2, Gate 0 draft)

**Status: specification only. Not implemented, not simulated.** Drafted
7 November 2026 on `codex/hybrid-routing-research`. It succeeds CHR-OE
(`CHR_OE_CANDIDATE_SPEC.md`) as the SOTA-directed candidate. CHR-OE stays in
the study as a comparator and as the source of the pressure-gate design.

"SOTA" is the goal, not a claim. The claim is earned only by passing §9
against the strongest comparators in §8.

---

## 1. Goal, stated so it can be tested

SAQR must:

1. **Match XY where XY is strong** (uniform traffic), within the agreed
   noninferiority margins (3% throughput, 10% p99).
2. **Beat or match the best of DyAD-OE, TOPSIS-OE and CHR-OE where they are
   strong** (transpose at 8×8–16×16).
3. **Close the gaps none of them closes:**
   - odd-even asymmetry (no westbound adaptivity);
   - a one-hop view (the 32×32 transpose reversal);
   - routing that ignores class;
   - hotspot congestion spreading;
   - adaptivity that costs uniform throughput.
4. **Stay competitive with published adaptive routers** at equal VC and buffer
   budgets (§8).

Two limits apply whatever the design. No policy beats XY by much on uniform
traffic, and no policy exceeds the cut or sink capacity
(`λ ≤ 4/k`, `λ ≤ 1/(0.2k²+0.8)`).

---

## 2. Deadlock handling: reservation, preservation, prediction

The user asked for deadlock freedom through reservation, preservation or
prediction instead of a plain dedicated escape VC. All three families are
already published:

| Family | Published examples (verified to the abstract or full-text level noted) | Fit for this router |
|---|---|---|
| **Reservation** (keep free buffer space) | Bubble flow control and the adaptive Bubble router (Puente et al., ICPP 1999, VCT tori); critical bubble scheme; worm-bubble (Chen & Pinkston, HPCA 2013); **FFC-CR** (Dai et al., DATE 2022, full text read): reserves credits *inside* a VC as a logical escape buffer, removing the dedicated escape VC | Bubbles target rings. Our mesh has no wraparound rings. FFC-CR's logical escape buffer is the closest prior art to "reserve a slot" |
| **Preservation / recovery buffers** | Static Bubble (Ramrakhyani & Krishna, HPCA 2017): extra recovery buffers at some routers | Costs extra buffers, which breaks equal-resource comparison |
| **Prediction / detection + recovery** | Probabilistic odd-even (adjusts risky turns at run time, with detection and recovery); SPIN (ISCA 2018): detect a cycle, then rotate it synchronously; SWAP (MICRO 2019): periodic adjacent swaps; DRAIN (HPCA 2020): periodic forced draining | Needs probes, synchronization or misrouting. Recovery moves can delay critical packets. Any guarantee rests on the recovery path, not on the prediction |

**Conclusion:** none of the three is a novel contribution by itself. This
router, however, has a property that permits a cheaper avoidance rule than a
dedicated escape VC.

### 2.1 Property: every VC holds at most one whole packet

The production config uses `wait_for_tail_credit = 1` and 8-flit VCs with
5-flit packets. A downstream VC is reallocated only after the previous
packet's tail credit returns, and the whole packet fits. A blocked packet
therefore occupies exactly one VC with its head at the front. That is the
virtual-cut-through (VCT) condition under which Duato's escape-channel theory
needs only *direct* dependencies. The SAQR build refuses to run if
`wait_for_tail_credit ≠ 1` or `depth < packet length` (same guard as CHR A1).

### 2.2 Rule: Compliance-Tracked Y-escape (CTY), a preservation rule

Call a packet in channel `c` **XY-compliant** if continuing with XY from `c`
uses only XY channel dependencies:

- every packet in an **X-direction** channel (E/W) is compliant, because a
  minimal packet moving east never needs west, and X→X and X→Y are XY turns;
- a packet in a **Y-direction** channel is compliant if and only if `dx = 0`.

The only non-compliant hop is a **Y move taken while `dx ≠ 0`** ("Y before X").

**CTY invariant (per Y-direction channel, per class):** at most one VC holds a
non-compliant packet. Implementation: non-compliant hops may use only the
class's designated VC (`class_base + 1`). Compliant hops may use any class VC.
X channels have no restriction. XY traffic is never restricted anywhere.

**Escape offer:** every route set also contains the XY port, at lower
priority, over all class VCs. This hop is always compliant, as just shown.
BookSim supports multi-port route sets with priorities (see `min_adapt_mesh`).
So a packet that prefers an adaptive port can still be allocated the XY port
if its preferred VC is unavailable.

**Proof sketch, to be written in full and checked mechanically (§6):**

1. In any reachable state, every full channel holds at least one compliant
   packet. X channels hold only compliant packets. A Y channel holds at most
   one non-compliant packet but has two VCs.
2. A compliant packet `q` in channel `c` requests its XY next channel `c'`.
   That is a dependency in the XY channel-dependency graph, which is acyclic.
3. Suppose a deadlock: a non-empty set of packets, none able to move. Ejection
   always drains. Take any blocked packet's requested XY channel. It is full,
   so it holds a compliant packet, which requests its own XY next channel, and
   so on. This walk follows the acyclic XY graph on a finite mesh, so it must
   end at a channel with a free VC (or at an ejection port). That packet can
   move. Contradiction.
4. Classes have disjoint VCs. Crossbar and links are not held across cycles
   (`hold_switch_for_packet = 0`). The weighted arbiter is work-conserving and
   grants best effort 1 of every 4 accepted grants while both classes are
   eligible, so best effort cannot starve.

**Relation to prior art:** CTY is Duato's VCT condition with XY escape, plus
the classical observation behind Double-Y / Mad-y routing (Glass & Ni) that
only the Y dimension needs a second channel class for fully adaptive minimal
2D mesh routing. FFC-CR reserves escape credit inside a VC. CTY instead
reuses the existing class VC pair without reserving buffer space. **This
combination is a resource-saving construction, not a claimed novel theory**;
it still needs a full-text check of Mad-y and FFC-CR.

**What it buys compared with a dedicated escape VC per class (BookSim
`min_adapt` style):** X-direction adaptive hops may use both VCs, and Y hops
by `dx = 0` packets may use both VCs. Only Y-before-X hops are limited to one
VC. Westbound packets gain full adaptivity, with no odd-even asymmetry.

### 2.3 Prediction as performance, not safety

Prediction never carries the guarantee. Predictors decide *when* to take
adaptive or restricted hops (§3). A wrong prediction costs performance and
cannot cause deadlock, because CTY plus the escape offer holds regardless.
SPIN/SWAP-style recovery is therefore unnecessary, and is not added unless the
§7 price-of-safety experiment shows CTY leaves a large gap.

---

## 3. Decision architecture (per head flit, class `c`)

Notation: `X` = XY port; `A` = the other productive port, if any.
`A` is non-compliant if it is a Y move with `dx ≠ 0`.

```text
if at destination:                         eject
if only one productive port:               {X : all class VCs}           # pure XY
if hot(dst) (endpoint congestion, §3.3):   {X : all class VCs}           # do not spread a sink's tree
if gate(c, X) is off (CHR hysteresis):     {X : all class VCs}           # exact XY when calm
if cost(A) + M <= cost(X):                 {A : allowed VCs (hi pri), X : all class VCs (lo pri)}
else:                                      {X : all class VCs}
allowed VCs for A = all class VCs if A is compliant, else {class_base+1}
```

The calm case is **exact XY with the same buffers**. This is the mechanism for
the uniform-traffic target, but whether it keeps XY's throughput is an
experimental question.

### 3.1 Local pressure (reused from CHR-OE, already unit-tested)

The class-local EWMA `e[c][p]` (α = 1/4) and hysteresis bit `h[c][p]`, with
occupancy normalized to the reachable capacity (A1). The gate opens when
`h[c][X] = 1`.

### 3.2 Regional pressure, destination-aware and bounded (DBAR-like)

Each router keeps a per-class, per-direction, 4-bit **row/column summary**:
congestion aggregated along that dimension, propagated hop by hop. Example rule:
`s_out = (local_e + s_in) / 2` in fixed point, i.e. a decaying sum that weights
nearer routers more. The selector compares `A` and `X` using a summary
truncated to the part of the row or column toward the destination (DBAR's
destination-based selection). This uses 4 directions × 2 classes × 4 bits =
32 bits of state. Control wires: 2 classes × 4 bits per direction per update
period. The update period (1, 4 or 8 cycles) is an ablation, and its wire and
energy cost is reported.

`cost(p) = (e[c][p] >> 2) + w_r · s[c][p] + (no free allowed VC ? F_PEN : 0)`,
with `w_r ∈ {0, 1/2, 1}`. Integer arithmetic only.

### 3.3 Endpoint-congestion isolation (Footprint-like, optional)

A router marks destination `d` **hot** when packets to `d` are observed blocked
at its ejection-side or final-hop outputs for more than `T_hot` cycles. Hot
marks live in a small per-router table of recently congested destinations (4
entries × (log₂ N + aging bits)). Packets to hot destinations take XY only, so
they stay on one path and do not spread a congestion tree across the adaptive
VCs that other flows need. Footprint (Fu & Kim, ISCA 2017) and HARE already
regulate adaptiveness under endpoint congestion. SAQR's variant is an ablation,
kept only if the hotspot pilot shows spillover onto unrelated flows. It cannot
add sink bandwidth.

### 3.4 Class awareness

All pressure inputs are class-local. The scheduler stays the frozen weighted
3:1 arbiter. Routing must not grant extra priority. Routing × scheduler
factorial runs are carried over from the agreed G4 design.

---

## 4. Cost budget (estimates, to be confirmed by synthesis)

| Item | Bits per router | Inter-router wires |
|---|---:|---:|
| Local EWMA + hysteresis | 56 | 0 |
| Regional summaries | 32 | 8 bits per direction per update |
| Hot-destination table (optional) | ≈ 4 × (10 + 2) = 48 at 32×32 | 0 (local observation only) |
| CTY compliance | 0 (designated VC); 1 bit per VC if dynamic | 0 |

The route stage needs two additions, a shift and a 5-bit compare per decision.
Whether that fits in one cycle is an assumption until G5 synthesis. A
`routing_delay = 2` sensitivity run is mandatory.

---

## 5. Implementation and isolation

Same discipline as CHR. New code goes in `algorithms/saqr/`, a new
`simulators/booksim_saqr/` adapter, a new build tree `.deps/booksim2_saqr`
built from the hash-checked frozen QoS tree, and results under
`results/saqr_study/`. Before any SAQR measurement the R0 regression gate is
rerun: XY, DyAD-OE and TOPSIS-OE must reproduce the frozen receipts exactly.

---

## 6. Correctness gates (G1)

1. **Exhaustive route tests** (all source–destination pairs, k ∈ {3, 4, 5, 8},
   random states): only productive ports are emitted; non-compliant hops are
   offered only the designated VC; the XY entry is always present; arrival
   takes exactly the Manhattan distance.
2. **Mechanical deadlock search:** an explicit-state model of the VCT network
   (one packet per VC, per-class VC pairs, CTY admission, escape offer) on
   2×2, 2×3 and 3×3 meshes. It searches for any non-empty configuration
   satisfying the invariant in which no packet can move.
   - **Expected:** none for SAQR.
   - **Negative controls that must find a deadlock:** unrestricted fully
     adaptive routing with both VCs unrestricted, and CTY without the escape
     offer.
   **Status, 7 November 2026:** implemented as `tests/saqr_deadlock_check.cpp`
   (greatest-fixed-point search over VC slots, which over-approximates reachable
   states). Results on 2×2, 2×3, 3×3, 4×4, 5×5 and 8×8 meshes:
   - XY, SAQR (CTY + escape offer) and Duato with a dedicated escape VC:
     **no deadlock configuration** on any mesh.
   - UFA: a deadlock configuration on every mesh.
   - CTY without the escape offer: a deadlock configuration from 4×4 up, none on
     2- and 3-wide meshes (edges prevent the closing hop; hand-traced on 2×2).
   This checks the routing-level argument only. Allocator fairness and the
   simulator implementation still need items 3–4.
3. **Runtime invariant assertion** in the simulator: never two non-compliant
   packets in one Y-channel class.
4. **Saturation stress runs** that must drain completely; integrity checks with
   zero errors; byte-identical determinism on repeat.

---

## 7. Experiments before any large sweep

- **Price of safety (falsifiable):** compare SAQR-CTY with **UFA**, an unsafe
  fully adaptive variant with both VCs unrestricted and a watchdog that aborts
  and flags any run with no progress for 10,000 cycles. If UFA, where it
  survives, beats CTY by more than the §9 margins, that justifies researching a
  recovery or reservation layer. Otherwise CTY is enough.
- **Ablations** (same build and traces):
  - `xy`;
  - plain Duato with a dedicated escape VC and local selection;
  - CTY with local selection only;
  - plus regional summaries;
  - plus the hysteresis gate;
  - plus hot-destination isolation;
  - full SAQR.
- **Pilot scope:** as in the CHR pilot (8×8, then 16×16; uniform, transpose
  and hotspot_center; seeds 101–103 for tuning only). Held-out evaluation uses
  seeds 201–205 on all four meshes and six traffic cases, in both scheduling
  modes.

---

## 8. Comparators required before any SOTA claim

All comparators use the same 2D mesh, 4 VCs, 8-flit buffers, 5-flit packets,
class partition and frozen weighted scheduler:

1. XY, OE-fixed, DyAD-OE, TOPSIS-OE, CHR-OE (already built or measured).
2. **West-first adaptive** (turn-model baseline with full westbound
   restriction).
3. **Duato minimal adaptive with a dedicated escape VC per class**, with the
   BookSim `min_adapt_mesh` VC-range issue corrected for class ranges.
4. **DBAR-style** destination-based regional selection on the same escape
   structure. Implemented from the paper's full text once obtained; until then
   labelled "DBAR-inspired".
5. **Footprint-style** endpoint regulation, if §3.3 is retained.

Re-implementations are labelled as such. Published numbers are never compared
directly with our simulator's numbers.

---

## 9. Acceptance criteria

The agreed CHR-OE §8 margins carry over unchanged (3% throughput, 10% p99,
paired lower and upper bounds over five held-out seeds). Two additions:

- **Difficult traffic:** SAQR is at least as good as the **best comparator in
  §8**, not only the project's three baselines, within the same margins, on
  transpose and hotspot families at k = 8 and 16. At k = 32 every metric is
  reported, and SAQR is expected to beat the k = 32 adaptive baselines' p99
  reversal against XY. If it does not, that is reported.
- **Safety:** zero deadlocks in the model search, all stress runs drain, zero
  runtime invariant violations.

Margins are not changed after data is seen. Failures are reported as failures.

---

## 10. Open items

- Read the full text of DBAR, Footprint, Mad-y/Double-Y and FFC-CR before any
  novelty statement. The novelty candidate is narrower than "SOTA routing": a
  **class-aware, exact-XY-when-calm, CTY-safe adaptive router with destination
  isolation and zero extra VCs**, shown to be Pareto-competitive. Whether that
  combination is publishable depends on the evidence and on that review.
- The CHR-OE 8×8 pilot (CHR spec §11) found that the odd-even path structure
  alone costs about 31–33% of XY's uniform throughput, and that CHR's margin and
  free-VC penalty slowed transpose adaptation. SAQR therefore starts with
  margin `M = 0` and `F_PEN = 0`; both stay as ablations, not defaults.

---

## 11. Implementation status (Gate 1), 7 November 2026

Built on `codex/hybrid-routing-research`:

- **Code:** `algorithms/saqr/routing.hpp` (SAQR variants `saqr`, `saqr_local`,
  `saqr_nogate`, and comparators `duato`, `westfirst`, `ufa`);
  `simulators/booksim_saqr/`; `scripts/setup_saqr.py` builds
  `.deps/booksim2_saqr`, which also contains the CHR routes.
- **Defaults** follow the CHR pilot: switch only on a strict cost improvement
  (`M = 0`), no free-VC penalty, regional weight 1/2. Hot-destination
  isolation (§3.3) is **not built yet**, because the CHR pilot showed
  hotspot_center to be sink-limited for every route. It returns only if a
  spillover diagnostic justifies it.

Gate 1 evidence:

| Check | Result |
|---|---|
| `tests/saqr_test.cpp`: all pairs k = 3–8, random states; XY entry always present; CTY VC rule; exact XY when calm; class isolation; Duato escape stickiness; west-first turn rule | PASS, 9.68M checks |
| `tests/saqr_deadlock_check.cpp` (§6.2) | PASS (see §6) |
| R0: SAQR binary reproduces frozen XY/DyAD/TOPSIS receipts | **144/144 identical** (`results/saqr_study/r0/r0_receipt.json`) |
| Runtime CTY / escape invariant on every in-network head flit (smoke runs) | ≈ 7M checks, 0 violations |
| Drain stress: 4 overload traces × 6 safe routes, everything delivered after the window, 30-minute hang timeout | **24/24 drained** (`results/saqr_study/stress/stress_receipt.json`) |
| UFA (unsafe control), 8×8 uniform at load 0.5 | **Class-level deadlock observed.** Best effort froze (0 delivered, 484 stuck) while critical traffic kept moving. The per-class watchdog now aborts and flags it |

**Smoke observations (single frozen seed-1 traces, plumbing only, not
evidence):**
- 8×8 uniform, load 0.5: SAQR throughput 0.287 vs XY 0.296.
- 8×8 transpose, load 0.5: `saqr_nogate` throughput 0.305, critical p99
  87 cycles.
- The gated variants adapt less on transpose (critical p99 about 104 cycles).
  The gate setting is the first tuning question.

**Not yet done:** the hand check of the new counters on a tiny mesh; the
written allocator-fairness argument; the tuning pilot (§7) with
price-of-safety and comparators on fresh seeds.

---

## 12. 8×8 tuning pilot, rounds 1–3 (7–8 November 2026)

Weighted mode, tuning seeds 101–103 (the same traces as the CHR pilot),
45 scenarios per variant. That is 765 SAQR-build runs plus 90 cross-check runs.
Every cross-check against earlier binaries was identical. R0 was rerun after
each rebuild: 144/144 each time. Zero integrity errors. Files:
`results/saqr_study/pilot_k8{,_r2,_r3}/` (`SUMMARY.md`, `paired.csv`).
Intervals are 3-seed paired t-intervals: exploratory and not
multiplicity-adjusted. These seeds are now **tuning data, not held-out data**.

Code changes made during tuning (each unit-tested; the defaults stay
bit-identical, confirmed by cross-check):
- **Asymmetry-ratio rule** (`NOC_SAQR_RATIO_NUM/DEN`): switch only if
  `cost(A)·num < cost(X)·den`.
- **Class-selective adaptivity** (`NOC_SAQR_CLASS_MASK`): unmasked classes
  route pure XY.

Main results (paired relative difference [95% CI]):

| Variant | Uniform throughput vs XY @0.3 / 0.4 / 0.5 | Transpose throughput vs TOPSIS-OE @0.5 | Transpose critical p99 vs TOPSIS-OE @0.5 |
|---|---|---|---|
| `saqr_nogate` (always compare) | −6.4 / −6.5 / −6.1% | **+11.6% [+11.3, +11.9]** | **−8.3% [−10.9, −5.7]** |
| `saqr` (gated) | −5.5 / −4.8 / −4.6% | +4.5% | +8.0% |
| `saqr_r2` (gated, ratio 2) | −5.3 / −4.5 / −3.6% | +2.5% | +12.1% |
| `saqr_slow_r32` (α = 1/8) | −5.2 / −4.4 / −3.9% | −1.1% | +17.3% |
| `saqr_nogate_crit` (only critical adapts) | **−1.8 / −2.5 / −2.9%** | −2.8% | **−8.3% [−12.8, −3.8]** |

Other findings:

- **Every SAQR variant beats DyAD-OE, TOPSIS-OE, plain Duato and west-first
  on uniform traffic** (for example `saqr` at 0.283 vs DyAD-OE 0.234 at load
  0.5). The cause is the exact-XY default instead of odd-even.
- **Price of safety:** the unsafe UFA control deadlocked on all 9 uniform
  overload runs and 1 hotspot run. Where it survived (transpose 0.5) it reached
  0.322 throughput against SAQR-nogate's 0.304. CTY costs about 5.5% of peak
  transpose throughput in exchange for guaranteed deadlock freedom.
- **Hotspot:** all routes are within noise of each other at the sink limit.
- **What did not work:** the regional summaries (`saqr` ≈ `saqr_local`),
  the ratio rule and the slow filter. None closed the uniform gap. Even rare
  switching (about 5–8%) costs uniform throughput, which suggests that myopic
  local switches move packets into equally loaded regions later on their
  paths. That is a hypothesis, not a measured mechanism.
- **No variant meets every agreed criterion at 8×8.** The uniform
  noninferiority bound (lower CI > −3%) fails for all variants. `saqr_nogate_crit`
  comes closest (−2.9% point estimate, −4.0% lower bound at load 0.5) and has
  the best transpose critical p99, but lower transpose total throughput than
  TOPSIS-OE. The variants form a **trade-off frontier**, not a single winner.

Proposed next steps (not yet run):
1. A 16×16 tuning stage for the three frontier points (`saqr_nogate`, `saqr`,
   `saqr_nogate_crit`) against XY, DyAD-OE, TOPSIS-OE and Duato. Scale is where
   the frozen adaptive baselines lose 35–43% of uniform throughput. Estimated
   cost: about 2 hours on 8 workers.
2. A two-tier variant: critical adapts freely, best effort adapts only under
   strong asymmetry.
3. Path-aware (two-dimensional) congestion information to address the myopic
   switching hypothesis, starting with a counter diagnostic that measures it.

## 13. 16×16 frontier stage (8 November 2026)

Runner `scripts/run_saqr_k16.py`, summary `scripts/summarize_saqr_k16.py`,
results `results/saqr_study/stage_k16/` (SUMMARY.md, summary.csv, paired.csv).
Weighted mode, tuning seeds 101–103 (fresh 16×16 traces, frozen generator),
uniform/transpose at indices 4–8 and hotspot-centre at 3–7: 45 cases × 8 routes
= 360 runs, all completed, zero integrity errors. Every route ran fresh on the
SAQR binary (sha ded01e1f…). **Anchor:** R0 only covered k = 4, 8, so before any
new run the SAQR binary replayed 9 frozen 16×16 receipts (xy/dyad/topsis,
seed 1, three traffics, load index 6): 9/9 identical.

Paired 95% intervals over 3 tuning seeds (exploratory, not multiplicity-adjusted).
Loads are offered flits/node/cycle; throughput is delivered.

| Comparison (16×16) | Uniform 0.15 / 0.20 / 0.25 | Transpose 0.15 / 0.20 / 0.25 |
|---|---|---|
| `saqr_nogate` vs XY, throughput | −17.3 / −16.2 / −15.2% | **+22.4 / +20.0 / +19.4%** |
| `saqr_nogate` vs TOPSIS-OE, throughput | +45 / +35 / +30% (means) | **+16.7 / +15.8 / +14.8%** |
| `saqr_nogate` vs Duato, throughput | +16 / +12 / +9% (means) | **+7.3 / +4.6 / +3.9%** |
| `saqr_nogate` vs TOPSIS-OE, critical p99 | ≈ equal | 0 / −5.3 / **−46.3%** |
| `saqr_nogate_crit` vs XY, throughput | −2.9 [−4.0,−1.8] / −4.5 / −5.4% | +1.9 / +2.9 / +4.9% |
| `saqr_nogate_crit` vs TOPSIS-OE, critical p99 | ≈ equal | 0 / −5.3 / **−46.4%** |

Findings:
- **Transpose at scale: `saqr_nogate` is the strongest route tested on every
  metric.** It delivers 19–22% more than XY, 15–17% more than TOPSIS-OE, 4–7% more
  than Duato, and halves critical p99 against TOPSIS-OE and Duato at the highest
  load (164 vs 305 and 314 cycles). XY itself saturates on transpose at 16×16
  (0.081 delivered at 0.10 offered; critical p99 4,360 cycles at 0.25).
- **Uniform at scale: the gap to XY grows for the always-adapt variants**
  (`saqr_nogate` −6% at 8×8, −15 to −17% at 16×16), consistent with the myopic
  switching hypothesis of §12. They still beat DyAD-OE, TOPSIS-OE, OE-fixed and
  Duato by a wide margin (DyAD-OE/TOPSIS-OE/OE-fixed collapse to 0.08–0.10).
- **Class-selective adaptivity scales better on uniform:** `saqr_nogate_crit`
  stays within 3–5.5% of XY, but lower bounds still fail the −3% criterion at
  0.20 and 0.25.
- **Critical p99 is carried by the critical class adapting:** `saqr_nogate`
  and `saqr_nogate_crit` give the same transpose critical p99, so the
  best-effort class's adaptivity buys throughput, not critical latency.
- **Hotspot-centre:** every route is sink-limited. SAQR variants are +1–2% over
  XY and +4–7% over TOPSIS-OE/DyAD-OE at the two highest loads (the OE
  adaptive routes lose slightly past saturation).

Conclusion: the two halves of the frontier are complementary by class.
Critical adaptivity gives the latency win at a much smaller uniform cost (−3 to −5.5%);
best-effort adaptivity gives the transpose throughput win but costs uniform
throughput when the network is symmetric. This motivates the two-tier
variant (§14): critical always adapts, best effort adapts only under strong
asymmetry.

## 14. Two-tier (per-class) variant (8 November 2026)

**Rule.** Critical traffic (class 0) always compares the two productive
ports with the additive rule (the `saqr_nogate` rule). Best effort (class 1)
adapts only under strong asymmetry: switch iff `costF(A)·num < costF(X)·den`,
optionally only while the hysteresis gate on the XY port is open. Implemented
as per-class overrides (`cls_gate`, `cls_ratio_num/den`, env
`NOC_SAQR_{CRIT,BE}_{GATE,RATIO_NUM,RATIO_DEN}`); −1 inherits the global
setting, so the defaults are bit-identical (unit test: 200,000 random states
with overrides equal to globals give identical route sets). The CTY safety
argument is unchanged: every route set still satisfies the §2 invariant
(checked structurally in `test_two_tier`). `saqr_test`: PASS, 16.54M checks;
`saqr_deadlock_check`: PASS.

**Build.** Rebuilt SAQR binary sha cdaa8509…79f8. R0 144/144 identical to the
frozen receipts. 8×8 round-4 cross-check 42/42 identical to earlier receipts
(xy, dyad, topsis, saqr, saqr_nogate, duato, saqr_nogate_crit). 16×16
cross-check 16/16 identical to §13 receipts.

Variants: `twotier_r2` (BE ratio 2:1, no gate), `twotier_g_r2` (gate + 2:1),
`twotier_g_r3` (gate + 3:1). 8×8: 135 runs (`results/saqr_study/pilot_k8_r4/`).
16×16: `twotier_r2` and `twotier_g_r3`, 90 runs
(`results/saqr_study/stage_k16_twotier/`). Zero integrity errors.

| Variant | Uniform thr vs XY, 8×8 (0.3/0.4/0.5) | Uniform thr vs XY, 16×16 (0.15/0.2/0.25) | Transpose thr vs TOPSIS-OE, 16×16 | Transpose thr vs Duato, 16×16 |
|---|---|---|---|---|
| `saqr_nogate` | −6.4 / −6.5 / −6.1% | −17.3 / −16.2 / −15.2% | +16.7 / +15.8 / +14.8% | +7.3 / +4.6 / +3.9% |
| `twotier_r2` | −6.4 / −6.1 / −5.5% | −14.7 / −14.3 / −13.0% | +12.0 / +11.7 / +11.3% | +3.0 / +0.9 / +0.7% |
| `twotier_g_r3` | −6.2 / −5.6 / −5.5% | −13.7 / −13.3 / −12.2% | +1.5 / +2.4 / +3.0% | −6.7 / −7.5 / −6.7% |
| `saqr_nogate_crit` | −1.8 / −2.5 / −2.9% | −2.9 / −4.5 / −5.4% | −2.8 / −0.7 / +0.8% | −10.7 / −10.3 / −8.8% |

Critical p99 is the same for all four (it is carried by the critical class,
which adapts identically in all of them): transpose 16×16 at 0.25 is −46% vs
TOPSIS-OE. Hotspot: all within ~1–2% of each other, sink-limited.

**Finding (negative).** Two-tier does not close the uniform gap. It moves
along the existing frontier: `twotier_r2` trades about 3.5–4.7 points of
transpose throughput for 2–3 points of uniform throughput relative to
`saqr_nogate`, and is dominated on neither side. The informative part is the
shape of the cost:
- **The uniform cost is not proportional to how often best effort switches.**
  With the gate and a 3:1 ratio, best effort switches on only about 3–4% of
  decisions (total switch rate 11.1% vs 7.7% for critical-only at 16×16, load
  0.25), yet uniform throughput drops from −5.4% to −12.2% vs XY.
- **Critical switches are cheap, best-effort switches are expensive.**
  Critical-only adaptivity switches on 7.7% of decisions and costs 5.4%.
  Hypothesis (not measured): critical packets win output arbitration 3:1, so
  their detours clear quickly, while detoured best-effort packets wait long in
  the single non-compliant VC (offset 1) of a Y link and in Y→X turns, blocking
  XY traffic behind them. The congestion estimate then cannot see the damage,
  because it is created downstream after the decision.

**State of the frontier after §12–§14 (tuning seeds only, no acceptance claim):**
- No SAQR variant meets the agreed uniform noninferiority criterion against XY
  at 8×8 or 16×16.
- `saqr_nogate` is the best safe route tested on transpose and is not beaten
  by DyAD-OE, TOPSIS-OE, OE-fixed or Duato on any traffic at 16×16.
- `saqr_nogate_crit` is closest to XY on uniform and matches the best
  critical p99, but gives up transpose total throughput against TOPSIS-OE
  and Duato.

**Proposed next steps (not yet run):**
1. A diagnostic first: per-switch downstream counters (wait cycles of the
   switched packet in the VC 1 of the Y link and at its Y→X turn, and blocking
   it imposes on XY packets) to confirm or reject the hypothesis above before
   designing against it.
2. A stall-triggered best-effort rule: best effort leaves XY only when its
   head flit has already waited `W` cycles for the XY output (reactive instead
   of predictive). On symmetric uniform load the XY port rarely stalls long, so
   the rule should rarely fire; on transpose, the XY port stalls persistently.
3. Turn-aware cost: add the expected cost of the later Y→X turn row (the
   downstream X-port pressure in the destination row) to `costF(A)`.

## 15. Hop-delay diagnostic and stall-triggered best effort (8 November 2026)

**Build.** SAQR binary sha 0a7cf473…87c9. New in this build:
1. A read-only per-hop delay diagnostic in `saqr_routes.cpp`. Hop delay is
   the number of cycles between a head flit's route calls at consecutive
   routers (VC wait + switch + link). Hops are classified by the output taken:
   X, X right after a Y→X turn, compliant Y, and non-compliant (detour) Y on VC
   offset 1. They are split by class and by whether the packet had already
   detoured.
2. A re-route hook in the study copy of `IQRouter::_VCAllocUpdate`. On a
   failed VC allocation an installed hook may ask for the head flit to be
   routed again in place (`setup_saqr.py`). The hook pointer is null unless
   the stall rule is enabled.
3. The stall rule (`saqr_stall_route`, env `NOC_SAQR_BE_STALL=W`). Best effort
   routes pure XY until its head has failed VC allocation for W cycles at
   that router. It is then re-routed once to {XY over both VCs at priority 1,
   other productive port at priority 0, VC offset 1 if non-compliant}.
   Re-routing a head flit that holds no downstream resource does not change
   the §2 argument: every route set it can receive is a subset of the SAQR
   route sets checked by `saqr_deadlock_check`.

**Checks.** `saqr_test` PASS with 17.61M checks, including `test_stall_route`
on k = 3, 4, 5, 8 and 16. R0 144/144 identical. Baseline cross-check 18/18
identical. Every diagnostic rerun (`saqr_nogate`, `saqr_nogate_crit`,
`twotier_g_r3`, 45 cases each) matched its earlier receipt exactly, so the
diagnostic is confirmed read-only. `saqr_xyref` (class mask 0, all-XY through
the SAQR code path) matched the frozen XY route on 45/45 cases. Round 5: 315
runs (`results/saqr_study/pilot_k8_r5/`, hop tables in `HOPS.md`), zero
integrity errors.

**Diagnostic (8×8 uniform at load index 7, best-effort class, mean cycles per hop, 3 seeds pooled):**

| Route | X | Y | Detour Y | X after Y→X turn | Detour share of hops |
|---|---:|---:|---:|---:|---:|
| XY (saqr_xyref) | 29.8 | 12.2 | — | — | 0% |
| saqr_nogate_crit (BE pure XY) | 30.9 | 12.6 | — | — | 0% |
| twotier_g_r3 | 37.0 | 17.1 | 12.5 | **64.2** | 4.6% |
| saqr_nogate | 38.0 | 21.5 | 41.3 | 45.6 | 11.4% |

Critical hops cost 5.2–5.7 cycles everywhere (critical wins arbitration 3:1).

What the diagnostic shows, and what it corrects in the §14 hypothesis:
- **With a selective rule, the detour hop itself is not slow.** Under
  `twotier_g_r3` detour Y hops cost 12.5 cycles, about the same as a normal Y
  hop under XY. So the §14 guess that detoured packets wait in the restricted
  VC is wrong for selective rules. It is right only for indiscriminate
  switching (`saqr_nogate`: 41.3 cycles).
- **The cost appears in two places after the decision:**
  - **The turn back into X:** 64 cycles under `twotier_g_r3`, against 37 for
    an ordinary X hop in the same run.
  - **Every packet that never detoured gets slower:** under `twotier_g_r3`,
    clean BE X hops rise from 29.8 to 37.0 cycles and Y hops from 12.2 to 17.1.

  Detours move load into rows and columns that are equally loaded on uniform
  traffic, and the cost falls on other packets. A local congestion estimate at
  the decision point cannot see either effect.
- **Critical detours are almost free for best effort.** Critical-only
  adaptivity raises BE X hops by only 1.1 cycles, which is why
  `saqr_nogate_crit` stays close to XY.
- **Transpose is the opposite regime.** Under XY, BE X hops cost 57 cycles
  and Y hops 5.0 (load index 7), a large imbalance between dimensions.
  Detoured packets then travel cheaply (after-detour X hops 11–15 cycles).

**Stall rule results (paired vs XY / TOPSIS-OE / Duato, 8×8, tuning seeds):**

| Variant | Uniform thr vs XY (0.3/0.4/0.5) | Transpose thr vs TOPSIS-OE (0.3/0.4/0.5) | Transpose thr vs Duato |
|---|---|---|---|
| stall_w8 | −7.9 / −7.2 / −7.1% | +4.4 / +6.3 / +7.0% | −1.0 / −0.5 / −0.6% |
| stall_w32 | −9.6 / −8.6 / −8.3% | −3.3 / −2.0 / 0.0% | −8.3 / −8.3 / −7.1% |
| stall_w128 | −5.6 / −6.5 / −6.6% | −9.9 / −6.7 / −4.8% | −14.6 / −12.7 / −11.5% |

**Finding (negative).** The stall rule is worse than the congestion rules on
uniform traffic at every W. Under uniform overload, XY outputs stall often
enough that the rule fires anyway (57,625 re-routes in one W = 32 run). A
long wait at one port does not distinguish a symmetric jam from an
asymmetric one. Large W suppresses re-routes but also removes the transpose
benefit. W = 32 does worse than both neighbours on uniform, probably because
it re-routes often after a long wait, which makes each detour both late and
frequent. That reading is a hypothesis. The 16×16 run was not done, because
the 8×8 result is clearly below the existing frontier.

**Revised understanding.** The obstacle to matching XY on uniform traffic
is not decision quality at the switching router. It is the externality of any
best-effort detour on symmetric load: extra cost at the Y→X turn plus slower
hops for everyone else. On transpose the same detours are cheap, because the
dimensions are strongly imbalanced. What separates the two regimes is a
property of the traffic pattern, the persistent imbalance between dimensions,
not the momentary state of one port.

**Proposed next step (not yet run):** a slow **regime detector** for best
effort. Each router keeps a long-horizon (for example 2^8-cycle) average of BE
X-port and Y-port pressure, pooled along its row and column like the regional
summaries. Best effort may adapt only while the X/Y imbalance stays above a
threshold. In these runs the XY hop-delay ratio is about 2.4 on uniform and
11–13 on transpose, a separable signal. Critical keeps adapting freely.
Uniform behaviour would then reduce to `saqr_nogate_crit` (−1.8 to −2.9% at
8×8), and transpose to `saqr_nogate` (+12% vs TOPSIS-OE). Whether a detector
built on buffer occupancy rather than measured delay separates them as
cleanly is the open question.

## 16. Regime detector for best effort (8 November 2026)

**Rule.** Every router keeps a slow EWMA (weight 2^-8 per cycle, fixed point
×256) of best-effort used credits on its X ports (E+W) and on its Y ports
(N+S). The detector at router (r, c) compares the row-r mean of X pressure (x)
with the column-c mean of Y pressure (y). The row/column pooling is computed
directly in the simulator and stands in for a summary network; at this time
constant, propagation latency is negligible, but that is an idealisation.
With hysteresis, the detector turns on when x > floor and x/y > ON, and stays
on while x > floor and x/y > OFF. Best effort may leave XY (under the
`saqr_nogate` additive rule) only at routers whose detector is on. Critical
traffic always adapts. Every route set is either an existing SAQR set or
pure XY, so §2 safety is unchanged. Code: `saqr_regime_next`,
`saqr_slow_next` (routing.hpp), detector and observe mode in
`saqr_routes.cpp`, env `NOC_SAQR_REGIME_{ON,OFF,FLOOR,SHIFT,OBSERVE}`.
`saqr_test` PASS, 17.76M checks (hysteresis truth table, EWMA convergence
without overshoot). Binary sha eb53723c…42c7. R0 144/144 identical.

**Calibration (observe mode, tuning traces, 90 runs, `results/saqr_study/regime_calib/`).**
Observe mode computes and logs the detector without gating. All 90 runs
reproduced their earlier receipts exactly. Pooled x/y ratio, 3-seed means:

| Traffic, load index 6–8 | BE on XY (`saqr_nogate_crit`) | BE adapting (`saqr_nogate`) |
|---|---|---|
| uniform | 1.80–1.92 (p95 2.4–2.8) | 1.15 (p95 1.3) |
| transpose | 2.93–3.64 (p05 2.3–3.0) | 1.63–1.68 (p25 1.5) |
| hotspot-centre | 6.3–7.1 | 1.25–1.28 |

Below saturation (indices 4–5) uniform and transpose-adapting sit near 1.0,
and transpose under XY at 2.2–2.6. Adaptation itself removes most of the
imbalance it responds to, so a single threshold would oscillate. Hysteresis
separates the regimes: turn on near 2.5 (reached by transpose under XY,
rarely by uniform), stay on while above 1.4 (transpose-adapting stays at about
1.65; uniform-adapting falls to about 1.15).

**Thresholds fixed before round 6** (chosen on tuning data, not held-out):
`regime_25_14` (ON 2.5, OFF 1.4), `regime_28_14` (ON 2.8, OFF 1.4),
`regime_22_14` (ON 2.2, OFF 1.4). All three use floor = 0.5 credits (128) and
shift 8. Round-6 runner: `scripts/run_saqr_pilot6.py`.

**Round 6 results** (8×8, tuning seeds, 135 runs, `results/saqr_study/pilot_k8_r6/`;
cross-check 42/42 identical, zero integrity errors). Detector-on share is the
fraction of router-cycles in the measurement window with the detector on.

| Variant | Uniform thr vs XY (0.3/0.4/0.5) | Uniform on-share | Transpose thr vs TOPSIS-OE (0.3/0.4/0.5) | Transpose on-share |
|---|---|---|---|---|
| saqr_nogate_crit (BE never adapts) | −1.8 / −2.5 / −2.9% | — | −7.6 / −4.1 / −2.8% | — |
| regime_28_14 | −2.8 / −3.6 / −5.1% | 8–15% | −4.6 / +2.3 / +3.6% | 42–56% |
| regime_25_14 | −6.2 / −5.6 / −6.0% | 13–19% | −2.9 / +3.9 / +5.5% | 48–62% |
| regime_22_14 | −6.8 / −6.4 / −6.6% | 19–25% | +1.2 / +6.1 / +5.9% | 58–70% |
| saqr_nogate (BE always adapts) | −6.4 / −6.5 / −6.1% | — | +12.5 / +12.4 / +11.6% | — |

Transpose throughput per seed tracks the on-share. At load index 7,
`regime_22_14` gives 0.2653, 0.2558 and 0.2722 with on-shares of 69%, 59% and
82%, against 0.280 for `saqr_nogate` on every seed. Paired intervals are
correspondingly wide (for example −16% to +18% vs TOPSIS-OE at index 6).

**Finding (negative).** In closed loop the detector neither stays off on
uniform nor stays on on transpose:
- **Uniform:** the detector is on 8–25% of the time, not the "rarely" that the
  open-loop calibration suggested. Fluctuations in individual rows and
  columns cross ON, and partial adaptation does not pull the ratio below OFF.
  That residual adaptation costs throughput.
- **Transpose:** the detector settles at a partial, seed-dependent on-share of
  40–80%. Adaptation flattens the imbalance it is measuring, so the detector
  hovers around OFF in parts of the mesh. Transpose then recovers only a third
  to a half of the `saqr_nogate` gain.
- **Overall:** the three variants again trace the same frontier between
  `saqr_nogate_crit` and `saqr_nogate`; none moves it outward. The 16×16 run
  was not done.

**Root cause.** Any detector that observes network occupancy observes its own
effect. Once best effort adapts, the uniform and transpose signals collapse
toward each other (§16 calibration: 1.15 vs 1.65). No threshold pair is robust
to both row-level noise and partial adoption.

**Where this leaves the design (tuning data, 8×8 and 16×16):**
- **Critical traffic:** adapting it is a clear win. Every critical-adaptive
  variant gives the best critical p99 of any safe route tested (−46% vs
  TOPSIS-OE on 16×16 transpose), at a uniform throughput cost of 2–5%.
- **Best effort:** its adaptivity is a genuine trade-off on this router and
  traffic set. Every rule tried trades uniform throughput against XY for
  transpose throughput: congestion threshold, ratio, slow filter, two-tier,
  stall-triggered and regime detection, ranging from always-adapt to never.
  The diagnostic (§15) locates the cost in the detours' externality: the
  turn back into X and slower hops for non-detoured packets.
- **Candidate operating points** for held-out evaluation:
  - `saqr_nogate_crit`: closest to XY on uniform, best critical p99. It needs
    an amended uniform criterion or accepts a −3 to −5% uniform cost.
  - `saqr_nogate`: best transpose and hotspot throughput, dominant over
    DyAD-OE, TOPSIS-OE, OE-fixed and Duato everywhere tested. It costs 6–17%
    against XY on uniform.

**Options not yet tried** that could move the frontier rather than slide
along it:
- **Open-loop regime information:** a detector fed by a quantity the routing
  does not change. One example is the imbalance BE *would* see under XY,
  estimated from destination statistics of injected packets
  (row/column demand matrices aggregated per region).
- **Non-minimal or two-phase routing for best effort** (Valiant-style
  randomisation, which balances transpose without per-hop decisions), compared
  against XY on uniform.
- **More VCs per class**, so the detour externality at the Y→X turn can be
  isolated. This changes the hardware budget and needs a fresh baseline set.

## 17. O1TURN-style plan for SAQR (8 November 2026)

**Motivation.** §16 listed "open-loop" information as the remaining way to move
the frontier. The simplest open-loop balancer is O1TURN (Seo et al., ISCA 2005):
each packet is assigned XY or YX at random, so transpose load splits across
both dimension orders without per-hop decisions. It was tested in two forms.

**Strict O1TURN (`o1turn`, routing `noc_o1turn_mesh`).** VC0 of each class is
the XY subnetwork and VC1 the YX subnetwork, with the plan bit
`(pid*2654435761u>>16)&1`. There is no escape and no crossing between
subnetworks. A runtime invariant aborts the run if VC0 makes a Y hop with dx≠0
or VC1 makes an X hop with dy≠0. Deadlock freedom (reservation: each
subnetwork is dimension-ordered on its own VC) is verified by
`tests/saqr_deadlock_check.cpp` policy O1TURN (2×2 through 8×8). The negative
control O1TURN_SHARED, where both orders share VCs, deadlocks as expected.

**Soft O1TURN in SAQR (`NOC_SAQR_O1TURN_MASK`, per-class bit).** A YX-planned
packet with rows remaining is offered the Y port on VC1 only, at priority 1. The
XY port is offered on both class VCs at priority 0. An XY-planned packet gets
the XY route set only. The plan is sticky: it is abandoned once the packet
moves in X while rows remain, after which the packet is pure XY. Every route set
is a subset of the existing SAQR/CTY set, so the CTY argument (non-compliant Y
hops on VC offset 1, XY escape always offered) carries over unchanged. Unit
tests (`test_o1turn`) cover the subset property. Variants:
- `saqr_o1t_be`: `saqr_nogate`, with the O1TURN plan applied to best effort only (mask 2).
- `saqr_o1t_both`: `saqr_nogate`, with the O1TURN plan applied to both classes (mask 3).

**Gates.**
- `tests/saqr_test.cpp`: PASS, 32,941,950 checks.
- Deadlock checker: PASS.
- Binary sha256 `f34be4ee…`, R0 144/144.
- Round-7 (8×8) cross-check against earlier receipts: 42/42.
- 16×16 cross-check against §13 receipts: 16/16.

### 17.1 Round 7, 8×8 (tuning seeds 101–103)

| comparison | saqr_o1t_both | saqr_nogate |
|---|---|---|
| uniform throughput vs XY (3 saturated loads) | −6.0 / −5.2 / −4.5% | −6.4 / −6.5 / −6.1% |
| transpose throughput vs TOPSIS-OE | +13.6 / +14.1 / +13.4% | +12.5 / +12.4 / +11.6% |
| transpose throughput vs Duato | +7.7 / +6.8 / +5.4% | — |
| transpose critical p99 vs TOPSIS-OE | −3.6 / −6.7 / −9.3% | — |
| hotspot | ≈ equal | ≈ equal |

- `saqr_o1t_be`: uniform −7.3 / −6.7 / −6.4% vs XY; transpose about +10% vs TOPSIS-OE.
- Strict `o1turn`: uniform −10 to −13% vs XY. Transpose critical p99 explodes (+136% and +3534% vs TOPSIS-OE). Hotspot −1 to −3%.

### 17.2 16×16 (stage_k16 traces, tuning seeds 101–103; 135 runs)

The results are in `results/saqr_study/stage_k16_o1t/SUMMARY.md`. Throughput is paired, as % of the reference, at the three saturated loads.

| traffic | candidate | vs XY | vs TOPSIS-OE | vs Duato |
|---|---|---|---|---|
| transpose 0.15/0.20/0.25 | saqr_o1t_both | +30.4 / +28.1 / +26.7 | +24.3 / +23.5 / +21.8 | +14.3 / +11.6 / +10.2 |
| transpose | saqr_o1t_be | — | +18.7 / +17.5 (0.20, 0.25) | +8.6 / +7.3 / +6.3 |
| transpose | saqr_nogate (§13) | +19.4 (0.25) | +15.8 / +14.8 (0.20, 0.25) | +7.3 / +4.6 / +3.9 |
| transpose | o1turn (strict) | +7.7 / +10.2 / +11.6 | +2.7 / +6.3 / +7.2 | −5.6 / −3.9 / −3.0 |
| uniform 0.15/0.20/0.25 | saqr_o1t_both | −17.4 / −14.8 / −14.7 | +44.8 / +37.0 / +30.4 | +15.9 / +14.1 / +9.8 |
| uniform | saqr_o1t_be | −18.5 / −19.0 / −17.4 | | |
| uniform | saqr_nogate | −17.3 / −16.2 / −15.2 | +44.9 / +34.7 / +29.6 | +16.0 / +12.1 / +9.2 |
| uniform | o1turn (strict) | −12.1 / −10.6 / −9.0 | | |
| hotspot (5 loads) | saqr_o1t_both | 0 to +1.5 | | |

**Critical traffic.**
- Transpose 0.25: critical p99 for `saqr_o1t_both` is 161 cycles against XY 4360 and TOPSIS-OE 305 (−47% vs TOPSIS-OE, −49% vs Duato), with 0 misses. Lower loads −4 to −7%.
- Uniform: critical p99 is within ±1% of XY.
- Strict `o1turn`: critical p99 collapses on transpose at 0.25 (4554 cycles, 57% misses), because critical packets lose the escape.

### 17.3 Reading

- **Result.** `saqr_o1t_both` is the new best SAQR operating point. It dominates `saqr_nogate` on transpose at both sizes: +6 to +8 points vs TOPSIS-OE at 16×16, with a better critical p99. It is equal or slightly better on uniform and hotspot. It also beats every adaptive comparator on every pattern tested. It uses fewer switches than `saqr_nogate` (12–20% vs 20–46%). The randomised plan spreads load that the per-hop rule previously spread only by reacting late.
- **Not solved.** The uniform gap to XY at 16×16 stays at −15 to −17%, and plan-only randomisation does not close it. Strict O1TURN loses less on uniform (−9 to −12%) but fails the critical-class and transpose criteria. Uniform saturation at 16×16 therefore favours pure dimension order on this 2-VC-per-class router. Any adaptivity costs here, consistent with §15's externality finding. The 3% uniform noninferiority criterion against XY is still not met by any adaptive variant at 16×16. That is recorded as an adverse result, not tuned away.
- **Candidate set for held-out evaluation (G4, seeds 201–205):** `saqr_o1t_both` (primary) and `saqr_nogate_crit` (uniform-closest). These are tuning-seed results only. No held-out claim is made.

## 18. G4 held-out evaluation protocol (frozen 8 November 2026, before any held-out run)

**Candidates (frozen in §17, no further tuning):**
- `saqr_o1t_both`: `saqr_nogate` with `NOC_SAQR_O1TURN_MASK=3`. Primary.
- `saqr_nogate_crit`: `saqr_nogate` with `NOC_SAQR_CLASS_MASK=1`. Uniform-closest.

All other SAQR defaults are as in §11. Binary sha256 `f34be4ee…` (R0 144/144).

**Comparators:** `xy`, `oefixed`, `dyad` (DyAD-OE), `topsis` (TOPSIS-OE), `duato` (escape VC per class), `westfirst`. DBAR-style and Footprint-style comparators (§8 items 4–5) are **not built**. Any SOTA statement from G4 is therefore limited to the comparators listed here.

**Matrix:**
- Meshes k = 4, 8, 16, 32.
- All six frozen traffic cases on the frozen nine-point load grids (`run_qos_grid.py`).
- Held-out seeds 201–205, with fresh traces from the frozen generator.
- Both scheduling modes: weighted (QoS) and age (matched control).
- Total: 1,080 cases × 8 routes × 2 modes = 17,280 runs.
- Runner: `scripts/run_saqr_g4.py`. Output: `results/saqr_study/g4`.

The protocol file hashes the binary, the routing and runner sources, the R0 receipt, and the evaluator. Every resume must match that hash.

**Tiers:** k = 4, 8 and 16 run first. Estimated at about 42 h wall on 8 jobs, from the frozen per-run times with about 1.9× contention. k = 32 is a separate tier, estimated at about 160 h wall. It uses the same protocol and needs a go-ahead.

**Criteria:**
- Pre-registered in `scripts/evaluate_saqr_g4.py`, written before any held-out run.
- They implement the CHR §8 margins and the §9 additions:
  - C1: uniform noninferiority vs XY.
  - C2: transpose vs the best comparator at k = 8 and 16.
  - C2h: hotspot families vs the best comparator at k = 8 and 16.
  - C3: hotspot and bursty vs XY.
  - C4: hidden-cost regressions, reported.
  - C6: safety.
- k = 32 transpose is reported with no pass/fail.

**Evaluator dry run.** Before the freeze, the evaluator was exercised once on the 16×16 *tuning* data (seeds 101–103, copied into a scratch directory). The dry run fixed one crash: a duplicate key in the paired record. No margin or rule was changed. On tuning data, the dry run already shows `saqr_o1t_both` failing C1 at saturated 16×16 uniform loads (throughput lower bound −16 to −19%). The held-out result is therefore expected to fail C1 there. That expectation is recorded now so it cannot be explained away later.

The seed 1–3 showcase reruns (CHR §7 "continuity, not held out") are not part of this tier.

## 19. SAQR-SC: source-classified SAQR (frozen 8 November 2026, before any SAQR-SC held-out run)

### 19.1 Motivation

The §17 soft-O1TURN set (`saqr_o1t_both`) wins on permutation traffic but loses 5–17% on uniform traffic at k ≥ 8, because adaptivity spreads uniform traffic away from the XY balance. The §16 regime detector failed because it was closed-loop: its congestion signal changed with the routing decision. SAQR-SC uses an open-loop signal that routing cannot influence, namely the *destination pattern of each source*.

### 19.2 Mechanism

- Each network interface keeps its last M = 4 destinations and an 8-bit EWMA (scale 256, shift 4) of the repeat-hit rate: `ewma += ((hit ? 256 : 0) − ewma) >> shift`.
- Hysteresis: the source turns adaptive when `ewma ≥ on` and turns deterministic when `ewma < off`.
- A packet's 1-bit class mark is fixed at injection and never changes in flight.
- Adaptive packets use the §17 soft-O1TURN SAQR route set (`saqr_o1turn_route`). Deterministic packets use exact XY over both class VCs.
- Both sets are subsets of the CTY-safe route sets: the XY escape over both VCs is always offered, and non-compliant Y hops use VC offset 1 only. The §9 deadlock argument therefore holds unchanged. This is **preservation**, not a new argument.
- Cost: about 49 state bits per network interface at k = 32, plus one header bit. Routers are unchanged.
- Known overfitting risk: under the frozen generator, uniform, bursty and hotspot destinations are random, so they classify as deterministic, while transpose has a fixed destination, so it classifies as adaptive. Unseen permutation patterns (bit-complement, shuffle, tornado) are needed to test generality. They are not yet implemented and are listed as future work.

### 19.3 Implementation and gates

| Item | Detail |
|---|---|
| Algorithm header | `algorithms/saqr_src/routing.hpp` (includes the unchanged `algorithms/saqr/routing.hpp`) |
| Simulator | `simulators/booksim_saqr_src/`, a separate build via `scripts/setup_saqr_src.py` |
| Binary sha256 | `4bf9ab50b504310d2eaef94089d51daa561a77eab34bc88a2414a4f54fc5225c` |
| G4 build | Untouched; protocol hashes stay valid |
| Unit tests | `tests/saqr_src_test.cpp`: PASS, 5,880,873 checks |
| R0 + X1 gate | `results/saqr_study/src/r0/r0_receipt.json`, sha256 `80b50206…`: R0 144/144 identical; X1 135/135 identical (classifier disabled reproduces rounds 1, 3 and 7) |

Unit tests cover:
- minimal routes;
- XY present at lowest priority;
- non-compliant hops on VC 1 only;
- deterministic packets taking exact XY;
- adaptive packets matching `saqr_o1turn_route`;
- EWMA bounds and history behaviour;
- hysteresis;
- uniform traffic adaptive for < 0.1% of packets at k = 8 and 16.

### 19.4 Tuning pilot (seeds 101–103; not held out)

- Script: `scripts/run_saqr_src_pilot.py`. 720/720 runs, 0 failures.
- Selection rule, fixed in the docstring before any SAQR-SC run: among variants whose uniform throughput lower bound vs XY is > −3% at every uniform load at both k = 4 and k = 8, pick the highest mean transpose throughput; ties within 0.5% go to `sc_128_64`.

| Variant | Uniform rule | Mean transpose throughput |
|---|---|---:|
| sc_128_64 (on 128 / off 64) | pass | 0.37194 |
| sc_96_48 | pass | 0.37184 |
| sc_192_96 | pass | 0.37205 |

**Selected: `sc_128_64`** (tie rule). `selection.json` sha256: `cbcebe37…`.

Observations on tuning data:
- **sc_never:** `sc_never` (classifier unreachable) is bit-for-bit equal to XY in throughput and latency at every point, which confirms the "exact XY when calm" claim.
- **8×8 uniform:** `sc_128_64` marks 0.0% of packets adaptive and equals XY, removing o1t_both's −4.5 to −6.0% deficit.
- **4×4 uniform:** within 0.2% of XY.
- **Transpose:** 100% of packets are marked adaptive and the result equals o1t_both.
  - 8×8: +21.7 to +25.6% vs XY and +5.3 to +7.1% vs the best comparator at loads ≥ 0.3.
  - 4×4: +3.2 to +4.7% vs the best comparator at loads ≥ 0.6.
- **hotspot_center:** 0–14% of packets adaptive. Equal to XY within noise and up to 1.6% (4×4) and 1.3% (8×8) behind TOPSIS. Like o1t_both, it does not lead on hotspot traffic.

### 19.5 Held-out (frozen)

- Script: `scripts/run_saqr_src_g4.py`. Candidate `saqr_sc` = `saqr_nogate` + `NOC_SAQR_O1TURN_MASK=3` + `sc_128_64`.
- It runs on the identical G4 traces (seeds 201–205, all six traffic cases, frozen load grids, both modes).
- Comparator receipts are copied from `results/saqr_study/g4` once each mesh is complete there.
- Scoring uses the unchanged pre-registered `scripts/evaluate_saqr_g4.py` (§18 criteria C1–C6 and margins).
- `protocol_src.json` hashes the sources, the R0 receipt, the pilot selection and the G4 protocol, and must match on resume.
- Order follows the user's instruction: k = 4 and 8 now, in parallel with the G4 tier; k = 16 after G4 k = 32.
- No G4 held-out result had been read when this section was written.

### 19.6 Held-out result, meshes 4, 8, 16 (scored 9 November 2026)

Runs:
- 4×4 and 8×8 ran in WSL.
- 16×16 ran on GitHub Actions from the byte-exact frozen bundle (`ci/saqr_actions/`), after a reproduction gate. The gate passed 70 of 70: 64 local held-out runs were bit-identical on Actions, and 6 traces at 16×16 regenerated byte-identically.

Scoring: the unchanged `scripts/evaluate_saqr_g4.py`. Output is in `results/saqr_study/src/g4/G4_VERDICT.md`.

| Criterion | Checks | Pass | Fail |
|---|---:|---:|---:|
| C1: uniform vs XY | 81 | 81 | 0 |
| C2: transpose vs best comparator (k = 8, 16) | 4 | 4 | 0 |
| C2h: hotspot vs best comparator (k = 8, 16) | 108 | 99 | **9** |
| C3: bursty and hotspot vs XY | 324 | 324 | 0 |
| C4: regressions vs XY | 0 | — | — |
| C6: safety | integrity errors 0, failed runs 0 | | |

Reading (weighted mode, mean of 5 held-out seeds):
- **Uniform and bursty:** identical to XY at every load. XY is itself the best route there, so SAQR-SC ties the best.
- **Transpose:** at 16×16, throughput is +23 to +30% vs XY and **+8.6 to +13.7% vs the best comparator** (Duato or West-first). At 0.5, critical p99 is 161 cycles, against 4274 for XY and 287 for the best comparator. At 8×8: +5 to +7% vs the best comparator at loads ≥ 0.6.
- **Hotspot (adverse, preserved):** the 9 C2h failures are all at hotspot_corner and hotspot_edge loads l5–l7, at or just above sink capacity.
  - SAQR-SC classifies hotspot sources as deterministic, because their destinations are random, so it equals XY.
  - DyAD, TOPSIS, OE-fixed and Duato deliver 4–11% more throughput there (lower bounds −4.2 to −10.8% against the −3% margin).
  - hotspot_center passes everywhere, within 2.2%.
- Conclusion: SAQR-SC is the best or tied-best route on uniform, bursty and transpose at k ≤ 16. It is **not** best on corner and edge hotspots near sink saturation. This is the gap identified for future work, an open-loop hotspot signal (§19.2); it is not a reason to retune this candidate.

### 19.7 Final held-out result, all meshes 4–32 (scored 9 November 2026)

32×32 ran on GitHub Actions (wave 2). Final verdict for SAQR-SC (`results/saqr_study/src/g4/G4_VERDICT.md`):

| Criterion | Checks | Pass | Fail |
|---|---:|---:|---:|
| C1 | 108 | 108 | 0 |
| C2 | 4 | 4 | 0 |
| C2h | 108 | 99 | 9 (the §19.6 hotspot points) |
| C3 | 432 | 432 | 0 |
| C4 | none | — | — |
| C6 | 0 integrity errors, 0 failed runs | | |

32×32 transpose is report-only. It gives +26 to +32% vs XY and **+12 to +18% vs the best comparator** at loads l5–l8. Critical p99 is 301 cycles at l8, against 1656 for the best comparator and 4535 for XY. 32×32 uniform equals XY at every load.

The original G4 candidates (same held-out, `results/saqr_study/g4/G4_VERDICT.md`):

| Candidate | C1 | C2 | C2h | C3 | C4 regressions |
|---|---|---|---|---|---:|
| `saqr_o1t_both` | 91/108 | 4/4 | **108/108** | 412/432 (bursty) | 26 |
| `saqr_nogate_crit` | 94/108 | 2/4 | 98/108 | 417/432 | 30 |

Both fail the uniform and bursty criteria, as recorded in advance in §18.

One infrastructure note: one 16×16 G4 run (k16_bursty_l6_s201, age, saqr_nogate_crit) was lost to an out-of-memory crash of the WSL host. It is not in progress.json because the runner process died. It was completed later on Actions, so "failed runs 0" refers to simulator failures only.

## 20. SAQR-H: SAQR-SC plus a hot-destination tracker (designed 9 November 2026)

### 20.1 Why

The 16×16 held-out (§19.6) showed one gap: SAQR-SC equals XY on corner and edge hotspots near the sink capacity, and adaptive routes deliver 4–11% more there. The G4 held-out confirms the cause from the other side: `saqr_o1t_both`, which is always adaptive, passes all 108 hotspot-vs-best-comparator checks, but loses uniform and bursty to XY.

Under the frozen generator, every hotspot source sends 20% of its packets to the hot node and the rest uniformly. SAQR-SC's repeat-rate signal sees only about 12% repeats there, well below its 50% switch-on threshold.

**Important: this design was made after seeing the 201–205 held-out results.** Those seeds are therefore no longer held out for SAQR-H. SAQR-H is tuned on seeds 101–103 and judged on fresh seeds **301–305**, with every comparator rerun.

### 20.2 Mechanism (`algorithms/saqr_hot/routing.hpp`)

Per source (network interface), on top of SAQR-SC:
- one candidate destination register and a 12-bit EWMA share `f` (x/4096);
- `f += (4096 − f) >> shift` when a packet goes to the candidate, `f −= f >> shift` otherwise;
- while `f < floor`, the candidate is replaced, but only by a destination that repeats one of the source's last 4 destinations (the SAQR-SC history, read before it records the packet);
- hysteresis on `f` (on and off) gives a second bit. The header bit is the SAQR-SC bit OR this bit.

Properties:
- The signal is open-loop: it depends only on destinations the source chose.
- Route sets are unchanged (SAQR-SC sets, CTY-safe), so the deadlock argument is the §9/§19 preservation argument.
- Cost: about 14 more state bits per network interface at k = 32 (a 10-bit candidate, a 12-bit share and 1 bit, minus shared logic). No new header bits.

Offline model at the real per-source packet counts:

| Setting | Uniform, 8×8 | Uniform, 16×16 | Uniform, 32×32 | Hotspot, 8×8 (measurement) | Hotspot, 16×16 (measurement) |
|---|---:|---:|---:|---:|---:|
| on .11, shift 4 | 6.3% | 0.6% | 0.0% | 97% | 89% |

At 32×32, a hotspot source injects only about 25 packets in total, so the tracker covers about half of them. 32×32 hotspot is scored only against XY, where adaptivity does not hurt.

### 20.3 Build and checks

| Item | Detail |
|---|---|
| Header | `algorithms/saqr_hot/routing.hpp` |
| Simulator | `simulators/booksim_saqr_hot/`, built by `scripts/setup_saqr_hot.py` |
| Binary sha256 | `598fba960ba972e117aae1d295a16ac2e3b5837295855b1c4af8f8f5eb0caf9a` |
| Unit tests | `tests/saqr_hot_test.cpp`: PASS, 4,255,014 checks; SAQR-SC tests still PASS |

The unit tests check:
- the header against an independent reference model over random parameters;
- separation at the design point;
- tracker off equals SAQR-SC exactly;
- combined bit = OR of the two bits;
- no adoption without a history repeat;
- parameter validation.

Smoke test (8×8, tuning seed 101):
- With the tracker off, the SAQR-H binary equals SAQR-SC exactly on all 3 cases.
- With h11:
  - edge hotspot l5: throughput +5.1%, adaptive 0.2% → 95%;
  - uniform l8: throughput −1.1%, adaptive 0% → 6.5%;
  - transpose: unchanged.

On Actions, the gate adds an equivalence check: every SAQR-SC reference run must reproduce on the SAQR-H binary with the tracker off.

### 20.4 Pilot and held-out (fixed before any pilot run)

The variant grid, the pilot cases and the selection rule are in the docstring of `scripts/saqr_h_study.py`. In brief:
- **Variants:** h11 (default), h13, h11s5, plus h_off (an equivalence check).
- **Pilot:** seeds 101–103, meshes 8 and 16, all six traffic cases.
- **Eligibility:** uniform and bursty throughput lower bound vs XY > −3% at every pilot load.
- **Choice:** the fewest hotspot points with lower bound ≤ −3% vs the best comparator; ties go to h11.
- **Held-out G5:** seeds 301–305, the full G4 design (k = 4–32, six traffic cases, 9 loads, both modes). Routes: the six comparators, `saqr_sc` and `saqr_h`.
- **Scoring:** the unchanged `scripts/evaluate_saqr_g4.py`.

### 20.5 Tuning-pilot result and selection (9 November 2026)

The pilot ran on GitHub Actions: 1782 runs, 0 failures. Its gate passed 86 of 86, including the new check that the SAQR-H binary with the tracker off equals SAQR-SC on every reference run. Inside the pilot, h_off equals saqr_sc on every point. Seeds 101–103 only. `results/saqr_study/hot/pilot/selection.json`:

| Variant | Uniform/bursty rule (worst lb vs XY) | Hotspot points ≤ −3% vs best | Mean hotspot throughput | Adaptive: uniform k8 / hotspot k8 / hotspot k16 |
|---|---|---:|---:|---|
| saqr_sc (reference) | pass (0.0%) | 10 / 30 | 0.03911 | 0% / 0% / 0% |
| h11 | **fail** (−4.0%) | 2 / 30 | 0.03992 | 6.6% / 96% / 88% |
| **h13** | **pass (−2.45%)** | **1 / 30** | 0.03991 | 3.2% / 93% / 83% |
| h11s5 | **fail** (−4.4%) | 1 / 30 | 0.03990 | 4.5% / 97% / 87% |

- **Selected:** h13, the only eligible variant. h11, the default design point, was excluded by the fixed uniform rule.
- **Transpose:** unchanged vs SAQR-SC (+5 to +14% vs the best comparator).
- **Remaining pilot weakness:** k16 hotspot_edge l5 vs TOPSIS (lb −4.05%).

## 21. Fresh held-out G5 and the "near-SOTA" test (frozen 9 November 2026, before any G5 run)

### 21.1 Purpose

The G5 claim being tested is **best or tied-best**: at every operating point a candidate must be no worse than the best of a stronger comparator set, within the frozen G4 margins. The test uses traffic never used for design or tuning and fresh seeds. The criteria are in `scripts/evaluate_saqr_g5.py`, written and hashed before any G5 run:
- **BT-T:** throughput lower bound > −3% vs the best comparator;
- **BT-L:** critical p99 within max(10%, 5 cycles) of the best comparator where it is not saturated;
- **XY:** never worse than XY;
- **S:** safety.

Strict wins (> +3%) are reported.

### 21.2 New comparators (`algorithms/dbar`, `algorithms/footprint`)

Both use the Duato framework of the study's Duato comparator: an XY escape VC (offset 0) and an adaptive VC (offset 1). They are deadlock-free by Duato's condition, checked by `tests/comparators_test.cpp` (23,131,823 checks) and by a simulator invariant on every head flit.

- **DBAR-style** (Ma, Enright Jerger and Wang, HPCA 2011): destination-truncated congestion summed along each candidate dimension. It is **idealized in DBAR's favour**: every router's previous-cycle occupancy is read with zero propagation delay.
- **Footprint-style** (Fu and Kim, HPCA 2017): with a free adaptive VC, it selects as Duato does. When congested, it follows the port whose adaptive VC holds a packet to the same destination.

The comparator binary (`simulators/booksim_saqr_x`, sha `94193fe2…`) was built on GitHub Actions from the byte-exact frozen tree (`ci/saqr_actions/qos_tree.tar.gz`). On Actions:
- all unit tests pass;
- 30 of 30 equivalence and smoke checks pass (`results/saqr_study/x_build/`);
- the new binary reproduces the frozen Duato, XY and SAQR-H runs bit for bit;
- DBAR and Footprint run with zero integrity errors.

The smoke runs show DBAR to be the strongest Duato-family route, e.g. 8×8 bit-complement 0.177 vs 0.159 for Duato.

### 21.3 Unseen traffic (`scripts/traffic_ext.py`)

Seven patterns: bitcomp, bitrev, shuffle, tornado, neighbor, multiflow (4 fixed destinations per source) and mixed (50% transpose partner, 50% uniform).

The last two are adversarial for the classifiers:
- **multiflow** cycles through 4 destinations (the history depth);
- **mixed** gives only a 50% repeat share.

### 21.4 Matrix

- Seeds 301–305; meshes 4, 8, 16, 32; 13 traffic patterns; frozen 9-point grids; weighted mode.
- 10 routes: xy, oefixed, dyad, topsis, duato, westfirst, dbar, footprint, saqr_sc, saqr_h (h13).
- **23,400 runs.** Protocol: `results/saqr_study/g5/protocol.json`, which hashes all four binaries, the sources, the evaluator and the pilot selection.
- Runs on GitHub Actions (stage `g5`, results branch `saqr-results-g5`).

### 21.5 Hardware cost (Yosys 0.33 on GitHub Actions)

Per network interface, k = 32 (10-bit ids), `rtl/saqr/saqr_h_classifier.sv`:

| Block | Xilinx 7-series (synth_xilinx) | Generic 2-input gates (abc) |
|---|---|---|
| SAQR-SC classifier | 61 LUT, 57 FF, 7 CARRY4 | 264 cells |
| **SAQR-H classifier** | **136 LUT, 83 FF, 22 CARRY4** | 605 cells |

Two pieces are still open:
- **Router reference:** Yosys 0.33 cannot parse the router's SystemVerilog interfaces, so a synthesized router reference is still missing. For scale, the router's input buffers alone hold 5 ports × 4 VCs × 8 flits.
- **RTL equivalence:** passes on Actions (Icarus Verilog). 74,023 of 74,023 vectors match the C++ model with the tracker on, and 74,023 of 74,023 with it off. The vectors mix uniform, hotspot, fixed-destination, flow-set and adversarial phases.
- **Build reproducibility:** the GitHub build reproduces the frozen comparator binary bit for bit (sha `94193fe2…`).

### 21.6 G5 verdict (10 November 2026): best-or-tied FAILS

All 23,400 runs completed on Actions (2 waves, 0 failed runs, 0 integrity errors, gate 86/86). Scored with the frozen `scripts/evaluate_saqr_g5.py`; full tables in `G5_VERDICT.md` on branch `saqr-results-g5`.

| Criterion (468 points per candidate) | saqr_sc | saqr_h |
|---|---:|---:|
| BT-T: throughput tied-or-better vs best of 8 | 389 | **399 (85 %)** |
| strict wins (> +3 % over the best of 8) | 21 | 21 |
| BT-L: critical p99 vs best (unsaturated points) | 467/468 | **468/468** |
| XY: never worse than XY | 414 | 414 |
| Safety | pass | pass |

The pre-registered claim ("best or tied at every point") is **not met**. It is recorded as an adverse result.

Where it fails:
- **XY beats every adaptive route on bitcomp, tornado and multiflow** (and on mixed at k ≥ 8). saqr_h's throughput at the top load is −9 to −11 % on bitcomp, −10 to −28 % on tornado and up to −16 % on multiflow, all against XY.
  - The classifier marks these permutations adaptive, like transpose and bitrev, because every permutation repeats destinations. saqr_all (every packet adaptive) is within ties of saqr_h there, so the loss belongs to the soft-O1TURN route set and not to the tracker.
  - Classic O1TURN beats saqr_h on tornado at k32 and on mixed. The likely cost is the route set's restriction of YX hops to VC 1.
- **DBAR:** 10 losses (mixed 9, hotspot_corner 1).
- **Footprint:** 0 losses.

Where it wins:
- Transpose: +14 to +29 % over XY at the top load.
- Bitrev: +22 to +48 % over XY at the top load.
- Strict wins over every comparator on both patterns, growing with mesh size.
- p99 never worse than the best comparator at any unsaturated point.

Win / tie / loss of saqr_h per comparator, out of 468 points:

| | xy | oefixed | dyad | topsis | duato | westfirst | dbar | footprint | o1turn |
|---|---|---|---|---|---|---|---|---|---|
| W / T / L | 59/355/47 | 145/309/8 | 131/328/3 | 130/326/4 | 104/352/5 | 137/326/3 | 79/374/10 | 104/364/0 | 95/333/34 |

- W: lower bound > +3 %. T: lower bound > −3 %. L: upper bound < −3 %. The remaining points are inconclusive.

### 21.7 O1TURN extension (stage `o1t`, frozen before its runs)

Routes: classic O1TURN, and saqr_all (the SAQR-SC classifier forced on). They ran on the G5 cases: 4,680 runs, 0 failures, 0 integrity errors. Scored with the frozen `scripts/evaluate_saqr_o1t.py`; tables in `O1T_VERDICT.md` on branch `saqr-results-o1t`.

| saqr_h vs | throughput tied-or-better | strict wins |
|---|---:|---:|
| o1turn | 428/468 | 95 |
| saqr_all | 463/468 (A-T) | 20 |
| best of 9 (B9-T) | 399/468 | 21 |

- Critical p99 vs O1TURN (unsaturated points): 462/462 for both saqr_sc and saqr_h.
- **Answer to "is it just O1TURN?":** no. saqr_h beats O1TURN outright at 95 points (uniform, bursty, transpose, bitrev, shuffle, hotspots) because it keeps XY where O1TURN splits needlessly.
- But O1TURN is not dominated: it wins 34 points (bitcomp, tornado, mixed, multiflow).
- The classifier itself adds little beyond the hotspot tracker: saqr_h vs saqr_all is 20 W / 3 L.

**Status:** the G5 seeds (301–305) are now spent. Any revised candidate must first be designed and tuned on other data, then frozen and tested on a fresh held-out seed set.

## 22. SAQR-C: the turn-column convergence cue (designed 10 November 2026, after §21.6)

### 22.1 Diagnosis (from G5, now design data)

- **The losses come from the cue.** Every G5 loss to XY is on a pattern where SAQR's repeat cue fires: bitcomp, tornado, multiflow and the transpose half of mixed. Each source there repeats one or a few destinations, so SAQR-SC marks it adaptive.
- **Adaptivity only pays when XY concentrates load.** That happens when many sources of a row turn into the same column: transpose, and bit reversal, where the destination column is a function of the source row. When row-mates turn at different columns (bitcomp, tornado, random flows), XY already meets the bisection bound and the adaptive route set only costs VC capacity.
- **Fully adaptive comparators do no better.** Duato, DBAR and Footprint all lose to XY on those patterns too.
- **A perfect cue would reach about 95 %.** An oracle choosing per point between XY and saqr_h would have been tied-best at 446 of 468 G5 points, with no loss to XY (means, approximate).

### 22.2 Mechanism (`algorithms/saqr_col/routing.hpp`)

Each router keeps a convergence tracker over the transit head flits that pass through it and still have X distance to cover:
- one candidate-column register;
- a 12-bit EWMA share f, updated per observed flit with weight 2^-5;
- candidate replacement when f < floor;
- an on/off hysteresis bit.

A packet injected at that router is adaptive (soft-O1TURN set) iff the router is converging, the packet's destination column equals the convergent column, and that column differs from the source column. Otherwise the packet takes exact XY.

Mode 1 also marks hotspot-like sources: the SAQR-H tracker bit is set while the SAQR-SC repeat bit is clear.

**Cost and safety:**
- Per router: one column register (log2 k bits), 12-bit share, compare logic. No new wires.
- The route sets are the SAQR-SC sets, so the §9 deadlock argument is unchanged.
- The runtime CTY invariant stays on.

### 22.3 Build and checks (GitHub Actions run 42789139411)

- **Binary:** `.deps/booksim2_saqr_c`, sha `da8fdf6f…`. The same job reproduced the comparator binary bit for bit (`94193fe2…`).
- **Unit tests:** `tests/saqr_col_test.cpp` passes 9,600,801 checks against an independent reference model, plus the full earlier suite.
- **Equivalence:** with the cue unset, the binary reproduces the comparator binary exactly on saqr_h, xy and dbar.
- **Smoke** (seed 101): share of packets marked adaptive by c50:

| Pattern | c50 |
|---|---:|
| transpose | 0.67–0.72 |
| bitcomp | 0.00 |
| tornado | 0.00 |
| uniform | 0.03 |
| mixed | 0.20 |
| hotspot_edge | 0.02 (0.91 with mode 1) |

### 22.4 Pilot (frozen before it ran: `scripts/saqr_c_study.py`)

- **Data:** G5 seeds 301–302; all 13 patterns; meshes 4–32; load indices 3–8.
- **Variants:** c50, c25, c50h, c25h. That is 624 cases × 4 = 2,496 runs (stage `cpilot`).
- **Reuse:** comparator receipts for the identical cases come from G5 and O1T.
- **Selection rule:** the most points with throughput at least 0.97 × the best of 9 comparators; tie → fewest points below 0.97 × XY; tie → simplest variant.

### 22.5 Fresh held-out G6 (defined before the pilot ran: `scripts/saqr_g6_study.py`, `scripts/evaluate_saqr_g6.py`)

- **Seeds:** 401–405.
- **Meshes:** 4–32.
- **Traffic (15 patterns):** the 13 G5 patterns plus two never used for design (butterfly, random permutation; `scripts/traffic_g6.py`).
- **Comparators (9):** G5's eight plus O1TURN.
- **Candidates:** the selected saqr_c, plus saqr_h for reference.
- **Criteria:** G5's, unchanged (BT-T, BT-L, XY, S), against the best of the nine comparators.
