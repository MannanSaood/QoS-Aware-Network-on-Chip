# DyAD-OE

`routing.hpp` switches between deterministic odd-even and congestion-adaptive
odd-even selection. Any virtual channel of a valid neighbor at >=60% occupancy
activates adaptation. Legal adaptive ports are ranked by aggregate occupancy.
This avoids averaging a full VC with three empty VCs and suppressing its flag.
Both modes stay within the same legal turn set; arbitrary XY/OE switching is unsafe.

```sh
python3 scripts/run_experiments.py --algorithms dyad --output results/dyad
```

Reference: Hu and Marculescu, [DyAD (DAC 2004)](https://doi.org/10.1145/996566.996638).
Our credit-based four-VC implementation adapts that design; see
`docs/METHODOLOGY.md` for differences from the original hardware/paper.
The corrected comparison protocol is in `docs/FAIR_COMPARISON_PROTOCOL.md`;
the old aggregate-trigger implementation is archived with the earlier results.
