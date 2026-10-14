# QoS-aware Network-on-Chip: XY, DyAD and TOPSIS

This project compares three separately implemented routing policies in BookSim,
with a two-class QoS extension, repeatable traffic, validation checks, and
MATLAB/Python plotting. NS-2 provides a secondary packet-network abstraction.
The simulation workflow does not require Vivado. The original SystemVerilog and
testbenches are retained; see the [original RTL README](docs/LEGACY_RTL_README.md).

## Current status

The intended showcase is the **3,888-run QoS comparison** across 4×4, 8×8, 16×16
and 32×32 meshes. As of 14 October 2026, the first three mesh sizes are complete
and 32×32 is still running with eight workers. The corrected single-class sweep
is paused with its completed evidence preserved. Final QoS figures are pending
completion and verification. See [project status](docs/PROJECT_STATUS.md) and the
[results guide](docs/RESULTS_GUIDE.md).

This is a **source-and-documentation release**: generated measurements, figures,
validation receipts, binaries and downloaded simulator trees are not in Git.
Paths under `results/` refer to local or regenerated artifacts. The separate
paper/Noxim investigation and isolated performance experiments are not included.

## Routing policies

| Folder | Policy | Scope |
|---|---|---|
| [`algorithms/xy`](algorithms/xy) | X-then-Y dimension-order routing | Deterministic baseline |
| [`algorithms/dyad`](algorithms/dyad) | DyAD-OE adaptation | Switches to legal odd-even adaptive candidates when the busiest VC reaches 60% pressure |
| [`algorithms/topsis`](algorithms/topsis) | Project TOPSIS-OE | Vector-normalized Euclidean TOPSIS over aggregate/peak credit pressure, with 0.7/0.3 weights |

These are documented project baselines. In particular, TOPSIS-OE is **not a
reproduction of the Yu et al. paper's router**. See the
[baseline registry](docs/BASELINE_REGISTRY.md) and
[routing audit](docs/ROUTING_COMPARISON_AUDIT.md).

## QoS experiment

All algorithms use the same timestamped demand trace, resources and timing:

- 25% critical and 75% best-effort traffic; four VCs of eight flits, split evenly
  between the classes; five-flit packets.
- Weighted 3:1 local class service with oldest-first ordering within each class.
  An age-only matched control uses the same class partition and resources.
- 5,000 warm-up and 20,000 measurement cycles, three seeds and nine offered loads
  per scenario. Loads scale with mesh size and traffic capacity references.
- Uniform, transpose, bursty on/off, and three fixed hotspot locations: corner,
  edge and center. Transpose is a spatial permutation, not on/off traffic.
- Four meshes × six traffic cases × nine loads × three seeds × three routes ×
  two scheduling policies = **3,888 runs**.

Main graphs show **critical-class p99 latency**, **total delivered throughput**
and **physical-port congestion**, with one metric per figure. Supporting tables
retain both classes' p50/p90/p99, backlog, deadline outcomes and fairness.
Plots use lines without point markers, consistent units and confidence bands.
Lower latency and higher throughput are desirable; low congestion alone does
not establish good performance. Completed-packet latency must be read alongside
unfinished demand, especially under overload.

The [QoS protocol](docs/QOS_EXPERIMENT_PROTOCOL.md) defines traffic, metrics,
arbitration and statistical limits. The
[readiness audit](docs/EVALUATION_READINESS_AUDIT.md) distinguishes implemented
simulator requirements from remaining hardware and research work. Weighted local
service does not guarantee end-to-end bandwidth or hard deadlines.

## Build and run on Ubuntu / WSL

Run from the repository root in a **fresh checkout**:

```sh
sudo apt-get update
sudo apt-get install -y git g++ make flex bison ns2 tcl-dev python3-numpy python3-scipy python3-matplotlib

# Download the pinned upstream BookSim and build our baseline adapters first.
python3 scripts/setup.py --jobs 2
# Build the separate QoS extension from that baseline.
python3 scripts/setup_qos.py --jobs 2
python3 scripts/validate_qos.py
python3 scripts/check_fr_coverage.py
python3 scripts/run_qos_grid.py --jobs 8
python3 scripts/prepare_qos_results.py
```

BookSim is pinned to commit `28f43299f1706a3160ffac721ca461d74eb6e618`.
Setup applies checked patches to downloaded sources under `.deps/`; the upstream
tree is not vendored. Python package requirements are also listed in
[`requirements.txt`](requirements.txt).

**Do not run setup, validation, or a second runner against an active study.**
The sweep freezes source, binary, configuration and trace provenance. Resume
with the same inputs; use a new checkout/output study for changed implementations.
Worker count changes host concurrency, not the experimental matrix.

Read-only progress inspection:

```sh
python3 scripts/sweep_status.py
python3 scripts/sweep_status.py --sections
```

The first command reports completed scenario groups; `--sections` counts
individual receipts, including completed runs within an unfinished group.

## MATLAB export

After the complete QoS dataset is prepared:

```matlab
addpath('matlab');
plot_primary_results('results/qos_report');
verify_primary_results('results/qos_report');
```

Exports include editable FIG files, vector PDFs and 300-dpi PNGs. The complete
report contains 72 individual charts and 10 comparison pages: eight pages for
p99/throughput across four meshes, plus two congestion pages. All six traffic
cases are represented. The individual library retains congestion for every mesh.
The pipeline does not create or edit PowerPoint slides.

On Windows, after the baseline setup above, use:

```powershell
.\run_qos_pipeline.ps1 -Jobs 8
# With an already completed dataset:
.\run_qos_pipeline.ps1 -PlotOnly -Matlab 'C:/Program Files/MATLAB/R2026b/bin/matlab.exe'
```

The wrapper builds/validates QoS if no protocol exists, otherwise resumes it.
Do not launch it while another runner/exporter is active. The older
`scripts/run_pipeline.ps1` targets the supporting single-class study, not QoS.

## Supporting studies and interpretation

The [corrected single-class protocol](docs/FAIR_COMPARISON_PROTOCOL.md) is kept
separate from the archived 2,160-run, shorter-window study. Do not pool their
measurements or rerun an archived implementation using changed source code.
The current local single-class study is paused and will not resume automatically.

For a small, separate BookSim/NS-2 check after baseline setup:

```sh
python3 scripts/run_experiments.py --sizes 4 --loads 0.1 --seeds 1 \
  --traffic uniform --warmup 100 --cycles 500 --output results/smoke
```

BookSim models flits, VCs, credits and router pipelines. Our NS-2 adapter models
packet store-and-forward links and queues; it does not implement the same
injection/ejection servers or VC machinery. It is a secondary model comparison,
not evidence that NS-2 is universally inaccurate. Simulator elapsed time is not
packet latency or measured routing hardware cost. See
[methodology](docs/METHODOLOGY.md) and [report design](docs/REPORT_DESIGN.md).

## Repository layout and future work

```text
algorithms/{xy,dyad,topsis,common}/  Routing policies and shared mesh helpers
simulators/booksim/                Project routing and measurement extension
simulators/booksim_qos/            Replay, scheduling, class checks and QoS metrics
simulators/ns2/                    Project NS-2 adapter
scripts/                          Setup, runners, validation and report preparation
matlab/                           Plotting and figure verification
tests/                            Routing, selector, traffic and QoS policy checks
experiments/                      Report configuration
docs/                             Protocols, audits and research plan
rtl/, tb/, include/               Original hardware and testbenches
```

The [hybrid research plan](docs/HYBRID_RESEARCH_PLAN.md) covers class-aware
congestion, bounded regional information, hysteresis, cheaper route selection,
deadlock constraints, scalable meshes and evidence-driven ablations. A new hybrid
and a state-of-the-art claim remain future research; neither is an achieved
result of this release.

Upstream references: [BookSim](https://github.com/booksim/booksim2) and
[NS-2 documentation](https://www.isi.edu/websites/nsnam/ns/ns-documentation.html).
