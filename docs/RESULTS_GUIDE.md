# Which results to use

This repository publishes source and documentation. Generated measurements,
figures and receipts under `results/` are local artifacts, excluded from Git.
Regenerate them with the README workflow in a fresh checkout. The dated
[project status](PROJECT_STATUS.md) records that the QoS 4×4, 8×8 and 16×16
matrices are complete while 32×32 is still running; it is not a live counter.

| Dataset | Purpose | Expected runs | Completion evidence |
|---|---|---:|---|
| `results/qos_comparison` → `results/qos_report` | Intended college-project showcase: two classes, weighted service, all three routes, with matched controls | 3,888 | `qos_comparison/progress.json`, then report `validation.json` and `figure_verification.json` |
| `results/fair_comparison` → `results/fair_report` | Corrected single-class variant comparison, retained as supporting evidence | 1,944 | Its progress and report verification files |
| `results/primary_grid` / `primary_report` | Archived earlier implementation; not the new showcase | 2,160 | Historical manifests; do not pool with corrected runs |
| Sibling `Paper-TOPSIS-Reproduction/results/cross_simulator` | Bounded shared-demand BookSim–Noxim comparison, then stop this investigation | 50 | `completion.json` and `REPORT.md` |
| Sibling `Paper-TOPSIS-Reproduction/results/paper_reference_runs` | Already completed characterization of the unchanged author Python release | 50 | Its protocol, raw runs and report |

The author-reference evidence was copied from the main repository to the sibling;
those copies are the same 50 runs, not two independent studies. The later 50
BookSim–Noxim runs are a separate experiment.

The bounded BookSim–Noxim comparison is complete: 25 paired cases / 50 runs,
with integrity checks passed and `scope_closed: true`. No additional Noxim or
paper investigation is planned.

`qos_preview` is explicitly partial. A successful preview verification proves its
curves match the selected completed runs; it does not certify the full sweep.
Use `complete: true` in the final report and its figure-verification receipt before
calling the showcase complete. No PowerPoint content has been changed.

Main QoS figures use critical-class p99 and total throughput, with congestion as
supporting context. Read `QOS_TRADEOFFS.md` and per-class data alongside the figures:
priority can improve critical service while reducing best-effort service or total
throughput. Smaller completed-packet latency alone is insufficient under overload.

Lower is better for latency, deadline-miss fraction and pending demand. Higher is
better for delivered throughput and within-class delivery fairness. Congestion
is a diagnostic: lower occupancy is not automatically better if throughput is
also lower. Simulator wall time is machine-dependent and is not router clock speed.

The congestion figure uses the frozen **aggregate physical-port** definition:
occupancy at least 60% across its four VCs. It is not a per-class pressure metric.
For example, two full best-effort VCs with two empty critical VCs represent 50%
aggregate occupancy, despite a full best-effort pool. Read this figure alongside
per-class source/network backlog and latency; a low value does not establish
that either class is uncongested. Class-pool occupancy instrumentation is a
possible addition for the next experiment, not a retroactive change to this one.

QoS host concurrency was increased from two to four workers after the Noxim
comparison finished. The running simulations were allowed to finish before the
coordinator was replaced. Two successful raw attempts without finalized result
receipts were archived under `qos_comparison/interrupted_attempts`; the resumed
runner repeats those same deterministic cases, rather than counting the attempts
as extra seeds. Administrative records preserve completed-receipt hashes, and the
final supervisor checks the archived metrics against the repeated results. This
changes host scheduling only, not simulated cycles or the frozen protocol. Wall
times collected across different worker counts are not a controlled runtime
benchmark.

The user subsequently requested pausing the supporting single-class sweep and
dedicating all eight workers to QoS. The old sweep is now paused: 1,533 successful
receipts and their raw evidence were hash-verified; four active case folders were
copied to `fair_comparison/interrupted_attempts/pause_20261014T021244Z` before
their processes were stopped. The top-level completed-case table has 1,530 rows;
three additional completed individual runs remain preserved in their case
folders. Incomplete attempts are administrative interruptions, not simulation
failures, and will restart with the same settings when explicitly resumed.
`fair_comparison/pause.json` records this state. Use
`python3 scripts/resume_fair_grid.py --jobs 4` only when resuming is requested;
it verifies the preserved evidence before and after the resumed study.

The previously waiting `build/rebalance_after_fair.py` was cancelled, as recorded
in `build/rebalance_after_fair.json`. The direct QoS four-to-eight worker handoff
uses the same checked helper and normal preservation audit under
`qos_comparison/interrupted_attempts/20261014T021624Z`.
The handoff preserved 2,105 completed QoS receipts, archived four successful raw
attempts whose receipts had not yet been finalized, and launched the unchanged
runner with eight workers. Eight active QoS simulator processes were confirmed;
the old single-class simulator processes are no longer running.

`scripts/finish_running_studies.py` is a one-shot Windows report pipeline for
the already-running studies. It waits for successful completion records (and
QoS resume-preservation checks), prepares the full measured datasets, then
exports and verifies 72 individual figures plus 10 comparison pages per study.
It never starts simulations or touches Noxim or the PPT. Its status and logs are
under `results/report_pipeline`; `--check` only reports readiness. Do not launch
another report export into the same destination while this pipeline is active.
The current reporter was restarted with `--studies qos`, so the paused
single-class study does not prevent the QoS report from completing.

## Simulator runtime audit

The local runtime audit (`results/performance_audit/REPORT.md`) profiles the existing
optimized build and checks host CPU, memory, and logging overhead. An isolated
bookkeeping candidate is in the local-only `simulators/booksim_performance`; it is not used by
the active sweep. The first link was slower. Restoring production object order
gave a 7.6% elapsed-time reduction on one balanced-order, full-duration 8×8
weighted-TOPSIS uniform workload (80.30 vs 74.18 seconds). This is not a measured
speedup for the entire matrix or a revised ETA.

The first candidate passed 48 separate event/metric equivalence pairs across all
four meshes and six traffic cases. The ordered build reproduced full-run metrics
in its timing checks. These audit runs are separate from the 3,888 showcase runs.
`results/performance_audit/decision.json` records that the candidate was not
deployed and that the frozen production binary, sources, and protocol remain
unchanged. The active QoS sweep retains eight workers and all original settings.
