# Baseline identities and claim limits

| Name | Implementation currently available | What its results can support |
|---|---|---|
| XY | Minimal X-then-Y routing in BookSim and NS-2 | Deterministic project baseline under the recorded resources/workload |
| DyAD-OE (adapted) | Deterministic/adaptive odd-even, busiest-VC 60% trigger, minimum aggregate-credit occupancy selection | Performance of this documented multi-VC adaptation; not exact original-paper replication |
| TOPSIS-OE (project) | Classical vector-normalized, Euclidean TOPSIS over two credit-pressure criteria with 0.7/0.3 weights and minimal OE candidates | Performance of this project-defined policy; not the Yu et al. 2025 router |
| Yu et al. released reference | Unmodified Zenodo Python archive, checksum verified; bounded characterization tests | Behavior of the released lightweight package, with limitations recorded in PAPER_REFERENCE_AUDIT.md |
| Yu et al. Noxim experiment | Original Noxim routing code/configurations/raw measurements have not been obtained | No completed reproduction or numerical validation of its published results |
| RCA / Q-RASP / other strong recent baselines | Literature identified; no validated port in this repository | Research comparators to implement or reproduce before a SOTA claim |
| Proposed QoS-aware hybrid | Research architecture only | Hypotheses and evaluation requirements; no measured QoS/SOTA result yet |

The original RTL and its validation are separate from these simulator baselines.
The frozen variant sweep uses one class. A separate validated two-class BookSim
build now implements weighted service and an age-only matched control; its new
sweep is the intended showcase dataset. See QOS_EXPERIMENT_PROTOCOL.md and
results/qos_validation/validation.json. Neither build changes previously measured
rows. The authorized 25 BookSim/Noxim paired cases (50 simulator runs) are now
complete, integrity-checked and closed. Their results are in the sibling
repository's `results/cross_simulator/REPORT.md`. This was a bounded engine
comparison, not a full paper reproduction or a determination about misconduct.

See QOS_EXPERIMENT_PROTOCOL.md for the active showcase,
FAIR_COMPARISON_PROTOCOL.md for the paused supporting study,
PAPER_REFERENCE_AUDIT.md for the released artifact, and HYBRID_RESEARCH_PLAN.md
for the proposed hybrid algorithm.
