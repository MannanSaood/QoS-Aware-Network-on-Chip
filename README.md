# QoS-Aware 3 × 3 Mesh Network-on-Chip (NoC)

## 1. Microarchitecture & Specifications
This network-on-chip is designed to support mixed-criticality system-on-chip (SoC) workloads, ensuring low-latency bounds for real-time traffic (e.g., sensor inputs, high-priority interrupts) while preserving throughput for best-effort bulk transfers.

- **Flit-Level Packet Format**: Parameterized at 34 bits:
  - `Flit[33:32]` → Flit Type (Head, Body, Tail)
  - `Flit[31:30]` → Priority Class (00: Real-Time, 01: High, 10: Best-Effort, 11: Low)
  - `Flit[29:24]` → Destination Coordinates (X, Y)
  - `Flit[23:0]` → Payload Data
- **Virtual Channel (VC) Regulator**: Every physical input port features 4 independent VCs. VC0 and VC1 are strictly dedicated to high-priority Real-Time flits. VC2 and VC3 handle lower-priority bulk data.
- **Allocation & Scheduling (TOPSIS Architecture)**: Employs a TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution) multi-criteria decision-making arbiter. Instead of fixed WRR, the arbiter dynamically evaluates three criteria: **Packet Priority Class**, **Flit Age**, and **Downstream Buffer Occupancy**. Flits are scored based on their Euclidean distance to the ideal positive and negative solutions, ensuring mathematically optimal QoS grants that inherently prevent starvation and dynamically balance load.

## 2. Implementation Milestones
- **Weeks 1–2 (Buffer Control)**: Code parameterized input queues with circular pointers per VC. Implement credit-based flow control backpressure signals to prevent upstream buffer overflows.
- **Weeks 3–4 (Arbitration & Switch)**: Implement the TOPSIS decision matrix hardware block (normalizing weights, calculating ideal solutions, and Euclidean distances). Develop the multiplexer-based 5 × 5 crossbar switch fabric.
- **Weeks 5–6 (Fabric Top-Level)**: Stitch the routers into a 3 × 3 mesh topology, binding local ports to configurable traffic generator endpoints.

## 3. Advanced Validation Techniques
- **Multi-Condition Expression Coverage**: Configure the simulator (VCS/Questa) to track nested control logic within the allocator. Create structural covergroups verifying the cross-product: `Buffer Fullness × Virtual Channel Availability × Packet Priority Code`. Ensure > 95% expression coverage is achieved under maximum traffic stress.
- **Congestion Testing via Synthetic Traffic**: Build a UVM agent that injects adversarial spatial traffic models, specifically alternating between Hotspot (all nodes targeting coordinate (1, 1)) and Tornado patterns.
- **Formal Property Verification (FPV)**: Write standard SystemVerilog Assertions (SVA) to formally prove starvation safety. We utilize **SymbiYosys (SBY)** as our open-source formal engine (which is fully cross-compatible with commercial tools like JasperGold):
  ```systemverilog
  assert property (@(posedge clk)
    (low_prio_request && !high_prio_request)[*16] |-> allocator_grant);
  ```
  This mathematically guarantees that a low-priority requests cannot be blocked for more than 16 cycles.
