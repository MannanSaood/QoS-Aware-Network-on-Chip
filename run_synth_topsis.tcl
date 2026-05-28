create_project topsis_synth vivado_synth_proj -part xc7a35tcpg236-1 -force
add_files rtl/allocators/topsis_arbiter.sv
set_property top topsis_arbiter [current_fileset]
synth_design -top topsis_arbiter -part xc7a35tcpg236-1
report_utilization -file reports/topsis_util.rpt
report_timing_summary -file reports/topsis_timing.rpt
exit
