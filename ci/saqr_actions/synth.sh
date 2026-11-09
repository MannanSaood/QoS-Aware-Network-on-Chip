#!/bin/bash
# Hardware cost on GitHub Actions with Yosys (open source; Vivado is not installable on a runner).
#  - SAQR-H classifier (rtl/saqr/saqr_h_classifier.sv, k = 32 ids) and its SAQR-SC-only variant,
#    mapped to Xilinx 7-series cells (synth_xilinx: LUT/FF counts, comparable to Vivado's
#    xc7a35t flow in run_synth.tcl) and to a generic 2-input gate library (gate count);
#  - the existing router RTL (run_synth.tcl's file list) as the size reference, if Yosys's
#    SystemVerilog front end accepts it (result recorded either way).
set -uo pipefail
OUT=${OUT:-$PWD/synth_out}; mkdir -p "$OUT"
yosys -V | tee "$OUT/yosys_version.txt"
for h in 1 0; do
  name=$([ $h = 1 ] && echo saqr_h || echo saqr_sc)
  yosys -q -l "$OUT/${name}_xilinx.log" -p "read_verilog -sv rtl/saqr/saqr_h_classifier.sv; chparam -set HOT_EN $h saqr_h_classifier; synth_xilinx -top saqr_h_classifier -flatten; tee -o $OUT/${name}_xilinx_stat.txt stat"
  yosys -q -l "$OUT/${name}_gates.log" -p "read_verilog -sv rtl/saqr/saqr_h_classifier.sv; chparam -set HOT_EN $h saqr_h_classifier; synth -top saqr_h_classifier -flatten; abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX; opt_clean; tee -o $OUT/${name}_gates_stat.txt stat"
done
FILES="rtl/noc/noc.sv include/router2router.sv include/input_block2crossbar.sv include/input_block2switch_allocator.sv include/input_block2vc_allocator.sv include/switch_allocator2crossbar.sv rtl/allocators/vc_allocator.sv rtl/allocators/switch_allocator.sv rtl/input_port/circular_buffer.sv rtl/input_port/rc_unit.sv rtl/input_port/input_buffer.sv rtl/input_port/input_port.sv rtl/input_port/input_block.sv rtl/crossbar/crossbar.sv rtl/router/router.sv"
if yosys -q -l "$OUT/router_xilinx.log" -p "read_verilog -sv $FILES; synth_xilinx -top router -flatten; tee -o $OUT/router_xilinx_stat.txt stat"; then
  echo "router synthesis: ok" | tee -a "$OUT/summary.txt"
else
  echo "router synthesis: Yosys front end rejected the router RTL (see router_xilinx.log)" | tee -a "$OUT/summary.txt"
fi
for f in "$OUT"/*_stat.txt; do echo "== $(basename $f)"; grep -E "Number of cells|LUT|FD|MUXF|CARRY|\\\$_" "$f" | head -20; done | tee -a "$OUT/summary.txt"
exit 0
