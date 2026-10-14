# TOPSIS-OE

`routing.hpp` implements full normalized TOPSIS over legal minimal odd-even
ports. Aggregate and peak per-VC credit occupancy are costs weighted 0.7 and 0.3.
Identical candidates tie deterministically; zero columns avoid division by zero.

```sh
python3 scripts/run_experiments.py --algorithms topsis --output results/topsis
```

This project-defined route selector differs from the legacy
`rtl/allocators/topsis_arbiter.sv`, a weighted linear score over requests.
NS-2's single link queue cannot express per-VC pressure, so both criteria reduce
to the same queue occupancy there. See `docs/METHODOLOGY.md`.
