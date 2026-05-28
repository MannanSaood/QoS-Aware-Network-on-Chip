# =============================================================================
# QoS-Aware NoC Router - Synthesis and Implementation Report Script
# Target: router (Hardware Metrics)
# Run: vivado -mode batch -source run_synth.tcl
# =============================================================================

set ROOT_DIR   [file normalize [file dirname [info script]]]
set SRC_DIR    $ROOT_DIR
set RPT_DIR    $ROOT_DIR/reports
set PROJ_DIR   $ROOT_DIR/vivado_synth_proj
set PROJ_NAME  "qos_noc_synth"
set TOP_MODULE "router"

# --- 1. Create directories ---
file mkdir $RPT_DIR
file mkdir $PROJ_DIR

# --- 2. Create project ---
create_project $PROJ_NAME $PROJ_DIR -part xc7a35tcpg236-1 -force

# --- 3. Add sources ---
add_files -norecurse [list \
    $SRC_DIR/rtl/noc/noc.sv \
    $SRC_DIR/include/router2router.sv \
    $SRC_DIR/include/input_block2crossbar.sv \
    $SRC_DIR/include/input_block2switch_allocator.sv \
    $SRC_DIR/include/input_block2vc_allocator.sv \
    $SRC_DIR/include/switch_allocator2crossbar.sv \
    $SRC_DIR/rtl/allocators/vc_allocator.sv \
    $SRC_DIR/rtl/allocators/switch_allocator.sv \
    $SRC_DIR/rtl/input_port/circular_buffer.sv \
    $SRC_DIR/rtl/input_port/rc_unit.sv \
    $SRC_DIR/rtl/input_port/input_buffer.sv \
    $SRC_DIR/rtl/input_port/input_port.sv \
    $SRC_DIR/rtl/input_port/input_block.sv \
    $SRC_DIR/rtl/crossbar/crossbar.sv \
    $SRC_DIR/rtl/router/router.sv \
]

# Set file types
set all_sv [get_files *.sv]
foreach f $all_sv {
    set_property file_type SystemVerilog $f
}

# --- 4. Synthesis ---
puts "\n===== Starting Synthesis: $TOP_MODULE ====="
set_property top $TOP_MODULE [current_fileset]
update_compile_order -fileset sources_1
synth_design -top $TOP_MODULE -part xc7a35tcpg236-1

# Reports after Synthesis
report_utilization -file $RPT_DIR/post_synth_util.rpt
report_timing_summary -file $RPT_DIR/post_synth_timing.rpt

# --- 5. Implementation ---
puts "\n===== Starting Implementation: $TOP_MODULE ====="
opt_design
place_design
route_design

# Reports after Implementation
report_utilization -file $RPT_DIR/post_route_util.rpt
report_timing_summary -file $RPT_DIR/post_route_timing.rpt
report_power -file $RPT_DIR/post_route_power.rpt
report_drc -file $RPT_DIR/post_route_drc.rpt

puts "\n===== Reports generated in $RPT_DIR ====="
puts "1. post_route_util.rpt  (Area/Resource usage)"
puts "2. post_route_timing.rpt (Timing/Delay performance)"
puts "3. post_route_power.rpt  (Power consumption)"

exit
