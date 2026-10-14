# Packet-level, store-and-forward NoC approximation using real NS-2 links/queues.
# Arguments: algorithm side arrivals.tcl output_prefix warmup cycles packet_flits
if {$argc != 7} {error "usage: ns mesh.tcl algorithm side arrivals prefix warmup cycles flits"}
lassign $argv algorithm k arrivals prefix warmup cycles flits
set root [file normalize [file join [file dirname [info script]] ../..]]
load [file join $root build nocroute.so] Nocroute
set ns [new Simulator]
$ns rtproto Manual
set tick 0.000001
set start [expr {$warmup*$tick}]
set stop [expr {($warmup+$cycles)*$tick}]
set capacity 8
set trace [open "$prefix.tr" w]
set events [open "$prefix.events" w]
$ns trace-all $trace
set occupancy 0.0
set congested 0
set samples 0
set linkcount 0
set delivered 0
set generated 0
set delivered_cohort 0
set seq 0

for {set i 0} {$i<$k*$k} {incr i} {
    set node($i) [$ns node]
    set agent($i) [new Agent/Message]
    $agent($i) set packetSize_ [expr {$flits*4}]
    $agent($i) set owner_ $i
    $ns attach-agent $node($i) $agent($i)
}
for {set i 0} {$i<$k*$k} {incr i} {
    set x [expr {$i%$k}]; set y [expr {$i/$k}]
    foreach p {0 1 2 3} delta [list 1 -1 $k [expr {-$k}]] {
        if {($p==0 && $x==$k-1) || ($p==1 && $x==0) || ($p==2 && $y==$k-1) || ($p==3 && $y==0)} {continue}
        set j [expr {$i+$delta}]
        set next($i,$p) $j
        # 32 bits per abstract cycle, one cycle link propagation.
        $ns simplex-link $node($i) $node($j) 32Mb 1us DropTail
        $ns queue-limit $node($i) $node($j) $capacity
        set queue($i,$p) [$ns monitor-queue $node($i) $node($j) ""]
        [$node($i) get-module Manual] add-route-to-adj-node $node($j)
        incr linkcount
    }
}

proc forward {id src cur dst born hops} {
    global ns agent next queue algorithm k capacity tick start stop events delivered delivered_cohort
    set now [$ns now]
    if {$cur==$dst} {
        if {$now >= $start && $now < $stop} {
            incr delivered
            puts $events "D $id [expr {($now-$born)/$tick}] $hops $src $dst"
        }
        if {$born >= $start && $born < $stop} {incr delivered_cohort}
        return
    }
    set loads {}
    for {set p 0} {$p<4} {incr p} {
        if {[info exists queue($cur,$p)]} {
            lappend loads [expr {double([$queue($cur,$p) set pkts_])/$capacity}]
        } else {lappend loads 0}
    }
    # NS-2 has one queue per link: total and peak criteria coincide here.
    set p [noc_select $algorithm $k $src $cur $dst $loads $loads]
    set j $next($cur,$p)
    $agent($cur) set dst_addr_ [$agent($j) set agent_addr_]
    $agent($cur) set dst_port_ [$agent($j) set agent_port_]
    $agent($cur) send "$id $src $dst $born [expr {$hops+1}]"
}
Agent/Message instproc recv {payload} {
    $self instvar owner_
    lassign $payload id src dst born hops
    forward $id $src $owner_ $dst $born $hops
}
proc generate {src dst} {
    global ns seq generated start stop
    set now [$ns now]
    if {$now >= $start && $now < $stop} {incr generated}
    incr seq
    forward $seq $src $src $dst $now 0
}
proc sample {} {
    global ns queue occupancy congested samples capacity stop tick
    if {[$ns now] >= $stop-0.1*$tick} {return}
    foreach key [array names queue] {
        set q [expr {double([$queue($key) set pkts_])/$capacity}]
        set occupancy [expr {$occupancy+$q}]
        if {$q>=0.6} {incr congested}
    }
    incr samples
    $ns at [expr {[$ns now]+10*$tick}] sample
}
proc finish {} {
    global ns trace events prefix generated delivered delivered_cohort occupancy congested samples linkcount
    $ns flush-trace
    close $trace
    puts $events "SUMMARY $generated $delivered $delivered_cohort $occupancy $congested $samples $linkcount"
    close $events
    exit 0
}
source $arrivals
$ns at $start sample
$ns at [expr {$stop+max(0.01,10*$stop)}] finish
$ns run
