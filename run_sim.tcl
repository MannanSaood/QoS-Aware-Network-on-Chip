# =============================================================================
# QoS-Aware NoC Router - Vivado 2024.2 Simulation Script (XSim direct)
# Run: vivado -mode batch -source run_sim.tcl
# =============================================================================

set ROOT_DIR   [file normalize [file dirname [info script]]]
set SRC_DIR    $ROOT_DIR
set PROJ_DIR   $ROOT_DIR/vivado_proj
set PROJ_NAME  "qos_noc_router"
set TOP_TB     "tb_router"

# --- 1. Create project directory ---
file mkdir $PROJ_DIR

# --- 2. Create a file-based project ---
create_project $PROJ_NAME $PROJ_DIR -part xc7a35tcpg236-1 -force

# --- 3. Set simulator ---
set_property target_simulator XSim [current_project]

# --- 4. Add sources: package first, then interfaces, RTL, then testbench ---

# 4a. noc_params package (must compile first)
add_files -norecurse [list \
    $SRC_DIR/rtl/noc/noc.sv \
]

# 4b. Interfaces
add_files -norecurse [list \
    $SRC_DIR/include/router2router.sv \
    $SRC_DIR/include/input_block2crossbar.sv \
    $SRC_DIR/include/input_block2switch_allocator.sv \
    $SRC_DIR/include/input_block2vc_allocator.sv \
    $SRC_DIR/include/switch_allocator2crossbar.sv \
]

# 4c. RTL bottom-up
add_files -norecurse [list \
    $SRC_DIR/rtl/allocators/vc_allocator.sv \
    $SRC_DIR/rtl/allocators/switch_allocator.sv \
    $SRC_DIR/rtl/input_port/circular_buffer.sv \
    $SRC_DIR/rtl/input_port/rc_unit.sv \
    $SRC_DIR/rtl/input_port/input_buffer.sv \
    $SRC_DIR/rtl/input_port/input_port.sv \
    $SRC_DIR/rtl/input_port/input_block.sv \
    $SRC_DIR/rtl/crossbar/crossbar.sv \
    $SRC_DIR/rtl/router/router.sv \
    $SRC_DIR/rtl/noc/node_link.sv \
    $SRC_DIR/rtl/noc/router_link.sv \
    $SRC_DIR/rtl/noc/mesh.sv \
]

# 4d. Testbench (goes in sim_1 fileset)
add_files -fileset sim_1 -norecurse [list \
    $SRC_DIR/tb/router/tb_router.sv \
]

# --- 5. Mark all .sv files as SystemVerilog ---
set all_sv [get_files *.sv]
foreach f $all_sv {
    set_property file_type SystemVerilog $f
}

# --- 6. Set simulation top ---
set_property top $TOP_TB [get_filesets sim_1]
set_property top_lib xil_defaultlib [get_filesets sim_1]

# --- 7. Update compile order ---
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# --- 8. Simulation properties ---
set_property -name {xsim.simulate.runtime}          -value {10000ns} -objects [get_filesets sim_1]
set_property -name {xsim.simulate.log_all_signals}  -value {true}    -objects [get_filesets sim_1]
set_property -name {xsim.elaborate.debug_level}     -value {all}     -objects [get_filesets sim_1]

# --- 9. Launch simulation ---
puts "\n===== Launching XSim: $TOP_TB ====="
launch_simulation

# --- 10. Run ---
run 10000ns

# --- 11. Print result ---
puts "\n====================================================="
puts "  Simulation complete. Check output above for:"
puts "    \[READ\] PASSED <time>  -- flit data matches expected"
puts "    \[READ\] FAILED <time>  -- mismatch detected"
puts "    \[All tests PASSED\]  -- full testbench pass"
puts "  VCD: $PROJ_DIR/qos_noc_router.sim/sim_1/behav/xsim/out.vcd"
puts "====================================================="

close_sim
puts "Done."
