# Audit of the released TOPSIS reference package

Audited 14 October 2026. This is an audit of the **released lightweight Python
package**, not of an obtained Noxim implementation or the paper's original raw
measurements. It does not establish fabrication, and it does not establish that
the project's BookSim results reproduce or disprove the publication.

Source: [Zenodo version 17063200](https://zenodo.org/records/17063200), reached
through the concept DOI linked by [the paper](https://www.nature.com/articles/s41598-025-20381-3).
Archive: `noc_topsis_reference_impl.zip`, 5,323 bytes.
MD5: `82a3d97c856e3bc116c330e7e8fecd3d` (matches the repository metadata).
SHA256: `394f023ffb464a965b10a6392852be5452ca1663f53f511489050b3172e01545`.
The unchanged archive and record metadata are retained under
`results/paper_reference_audit`. Extracted source is under
`.deps/paper_topsis_reference/source`. Source hashes and executable-check
results are in `results/paper_reference_audit/validation.json`.

## Verified behavior of this release

| Finding | Source / executable evidence | Implication |
|---|---|---|
| Throughput counts hop transmissions | `src/mesh.py:104,108`; one delivered six-hop packet over ten ticks reports 0.6 | This is neither delivered packets/tick nor delivered flits/node/cycle; route length changes the reported value |
| Warm-up is included in statistics | `src/mesh.py:106-110`; a packet delivered entirely during a one-tick warm-up still gives throughput 0.1 and latency 1 over the following ten empty ticks | Measurement boundaries differ from our BookSim window |
| Router traversal depends on loop order | `src/mesh.py:88-104`; a six-hop (0,0)->(3,3) packet completes in one tick, while the reverse needs seven ticks | In-place queue updates permit several forward hops within a single tick |
| Congestion readings are identical across output ports | `src/mesh.py:91-92` feeds the same local input-queue length to every port's identically initialized filter; the controlled test confirms equality | The supplied congestion criterion cannot distinguish outgoing directions in this implementation |
| A known failed output can remain selected | `src/mesh.py:39-59,101`; with east failed at (0,0), destination (1,0), the selector picks east and the packet remains blocked for 20 ticks despite a healthy detour | The released selection/retry combination does not deliver that simple fault case |

These tests run the unmodified released classes with deterministic injected
packets. Re-run with `python scripts/audit_paper_reference.py`. They characterize
specific counterexamples; they are not a benchmark of the full paper.

Additional static observations: the packet structure has no priority, service
class or deadline; `RouterCfg.vcs` is declared but not used for VC allocation;
input queues are not capacity-limited; the package contains no XY, DyAD or EDAR
implementations and no transpose/shuffle traffic generator. The example command
uses a fixed seed and does not offer a seed argument, although `Mesh` accepts one.
Consequently this archive alone does not reproduce the paper's comparative
experiment matrix.

The released selector calls itself a two-stage TOPSIS-like index. It uses column
sum normalization and weighted sum/maximum regret terms, then a Q score with
v=0.6. Our project selector uses Euclidean ideal/anti-ideal distances after vector
normalization. These are different decision kernels as well as different input
criteria. Passing our TOPSIS arithmetic tests is not a fidelity test against this
released kernel.

## What to do with this evidence

1. Preserve the current BookSim sweep as a clearly named project-variant study.
   The user explicitly asked to let it finish while this reference is investigated.
2. Keep released-code reproduction and improved-model porting separate. Fixing
   its simulator semantics would create a corrected variant, not reproduce the
   released implementation unchanged.
3. Seek the original Noxim routing source, configurations and raw outputs if
   publicly available. No author contact has been sent. Without them, disclose
   which implementation details remain unresolved.
4. A BookSim port of the released decision kernel would require explicit
   definitions of congestion sampling, fault handling, candidate legality,
   deadlock/livelock control, VC resources and routing delay. Test selector
   equivalence first; do not silently import the lightweight simulator's time
   or throughput semantics.
5. For a new QoS-aware hybrid, define service classes and objectives explicitly.
   Give all routing baselines the same scheduler and resources, then ablate
   scheduling and routing independently. QoS differentiation is an additional
   project objective, not evidence that the existing paper was replicated.

The useful conclusion is a documented reproducibility gap in the released
artifact. This is not a basis for claiming fraudulent results or for presenting
our project-defined TOPSIS-OE as the paper's router.
