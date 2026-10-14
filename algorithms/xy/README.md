# XY

`routing.hpp` preserves dimension-order routing: X then Y, minimal hops.
The original hardware counterpart remains in `rtl/input_port/rc_unit.sv`.
Both simulator adapters compile the same C++ selector.

```sh
python3 scripts/run_experiments.py --algorithms xy --output results/xy
```

Select a backend with `--simulators booksim` or `--simulators ns2`.
This implementation is regression-checked against BookSim's built-in `dim_order`.
