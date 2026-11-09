# SAQR held-out runs on GitHub Actions

This directory runs the remaining frozen held-out matrices on GitHub-hosted runners:
- G4 (`docs/SAQR_SPEC_V2.md` §18);
- SAQR-SC (§19).

It covers meshes 8, 16 and 32, all 8 G4 routes plus `saqr_sc`, both modes, and seeds 201–205. Nothing about the protocols changes.

## Workflow

`.github/workflows/saqr-heldout.yml` lives on `master`, because scheduled workflows only run from the default branch. It runs every 6 hours (cron `17 */6 * * *`) and can also be started by hand.

| Step | What it does |
|---|---|
| **verify** | Every job unpacks `bundle.tar.gz`. It holds the hashed sources, both frozen binaries and the receipts, byte-exact, which avoids git line-ending conversion. The job then recomputes both protocols and requires them to equal the frozen `protocol.json` and `protocol_src.json`. It also checks numpy 1.26.4 and Python 3.12, the versions that generated the local traces. |
| **gate** | Runs once per bundle. It regenerates held-out traces, including at k = 16, and requires byte-identical traces. It reruns a sample of locally completed held-out runs (both binaries, all routes, both modes), which must reproduce bit for bit. Lanes run only after the gate passes. |
| **lanes** | N lanes, 10 by default, 4 simulations each. Remaining cases are dealt round-robin, longest first. A lane starts new runs only before 5.0 h and kills any run still going at 5.5 h; those rerun next wave. Every finished `result.json` is uploaded. |
| **merge + check** | Commits new receipts to the `saqr-results` branch and updates `ci_status/STATUS.md`: progress per mesh and stage, failures, ETA. It also updates `ci_status/traces.json`, which records trace shas and flags any conflict. On run failures, a trace mismatch or a failed gate, it writes `ci_status/ALERT` and fails the workflow, so GitHub notifies. Results are saved first. |

## Local commands

| Command | What it does |
|---|---|
| `python3 ci/saqr_actions/make_bundle.py` | Rebuilds the bundle, run in WSL. A new bundle re-triggers the gate. |
| `python3 ci/saqr_actions/fetch_results.py` | Copies Actions receipts into `results/`. Overlapping runs must be identical. |
| `python3 scripts/run_saqr_src_g4.py --collect --meshes 8 16`, then the evaluator | Scores the results as before. |
