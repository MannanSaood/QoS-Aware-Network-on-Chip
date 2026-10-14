# Source release and experiment status

Snapshot: **14 October 2026, 19:58 IST**. This is a dated record, not a live counter.

| QoS mesh | Completed individual runs | Planned runs |
|---|---:|---:|
| 4×4 | 972 | 972 |
| 8×8 | 972 | 972 |
| 16×16 | 972 | 972 |
| 32×32 | 329 | 972 |
| Total | 3,245 | 3,888 |

At this snapshot, 32×32 uniform was complete (162 runs), transpose had 149 runs
and bursty had 18. Eight workers were active, with no recorded failed cases.
The full showcase was not yet complete. A separate report process waits for
completion and preservation checks before preparing and verifying final figures.
Use `python3 scripts/sweep_status.py --sections` for current local counts.

## What this commit publishes

Project-authored routing headers, BookSim/NS-2 adapters, QoS runtime and arbiters,
setup/runner/validation/report scripts, tests, MATLAB plotting and documentation.
Existing RTL and its historical validation are a separate body of work.

Generated `results/`, downloaded `.deps/`, build products, host-specific profiling
experiments and copied upstream performance-candidate sources remain local and
are ignored. The sibling `Paper-TOPSIS-Reproduction` repository is not part of
this release. References to these local artifacts document provenance; cloning
this repository alone does not download the measured datasets or figures.
No raw data were deleted to prepare this source release.

## Evidence and limits

The QoS integration and directed tests passed before the sweep: class-preserving
VCs/payloads, common demand replay, actual router service differentiation,
deadline accounting and packet conservation. FR1/FR2 and the revised weighted
FR3 are implemented at simulator level; this is not a new RTL sign-off or proof
of hard real-time guarantees. Validation receipts can be regenerated using the
README commands in a fresh checkout.

The corrected single-class study is paused with 1,533 successful receipts
preserved. Its top-level table has 1,530 rows because three individual receipts
belong to unfinished scenario groups. It will not resume automatically.

The bounded sibling comparison completed 25 BookSim/Noxim pairs (50 runs) and
is closed. Similar directional trends under shared demand do not establish
identical simulator timing, validate the paper's unpublished configuration, or
demonstrate misconduct. Project TOPSIS-OE remains a separate implementation.

The isolated runtime candidate was not deployed. The active QoS run still uses
the frozen simulator and unchanged experimental conditions. No PowerPoint was
modified. Hybrid algorithm development remains future work.
