// Replays C++-model vectors through rtl/saqr/saqr_h_classifier.sv; every mark must match.
// iverilog -g2012 -P saqr_h_classifier_tb.HOT_EN=1 -o tb rtl/saqr/saqr_h_classifier.sv tests/rtl/saqr_h_classifier_tb.sv
// vvp tb +vectors=<file>
`timescale 1ns/1ps
module saqr_h_classifier_tb;
    parameter int HOT_EN = 1;
    logic clk = 0, rst_n = 0, in_valid = 0;
    logic [9:0] in_dest = '0;
    logic mark;
    saqr_h_classifier #(.DW(10), .HOT_EN(HOT_EN)) dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_dest(in_dest), .mark(mark));
    always #5 clk = ~clk;
    string path;
    integer fd, d, e, n, bad, r;
    initial begin : replay
        if (!$value$plusargs("vectors=%s", path)) begin $display("FAIL: no +vectors"); $finish; end
        fd = $fopen(path, "r"); if (fd == 0) begin $display("FAIL: cannot open %s", path); $finish; end
        n = 0; bad = 0;
        repeat (3) @(posedge clk); rst_n = 1;
        while (!$feof(fd)) begin
            r = $fscanf(fd, "%d %d\n", d, e);
            if (r != 2) break;
            @(negedge clk); in_valid = 1; in_dest = d[9:0];
            #1;
            if (mark !== e[0]) begin
                bad++;
                if (bad <= 10) $display("MISMATCH vector %0d dest %0d: rtl %0b model %0d", n, d, mark, e);
            end
            n++;
            @(posedge clk);
        end
        @(negedge clk); in_valid = 0;
        if (bad == 0 && n > 0) $display("PASS: %0d vectors, HOT_EN=%0d", n, HOT_EN);
        else $display("FAIL: %0d mismatches of %0d vectors", bad, n);
        $finish;
    end
endmodule
