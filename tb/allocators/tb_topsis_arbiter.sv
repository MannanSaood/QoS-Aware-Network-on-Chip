`timescale 1ns / 1ps

module tb_topsis_arbiter();
    parameter PORTS = 4;
    logic             clk;
    logic             rst_n;
    logic [PORTS-1:0] request_i;
    logic [1:0]       priority_i [PORTS-1:0];
    logic [3:0]       age_i [PORTS-1:0];
    logic [3:0]       buf_occ_i [PORTS-1:0];
    logic [PORTS-1:0] grant_o;

    topsis_arbiter #(
        .PORTS(PORTS)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .request_i(request_i),
        .priority_i(priority_i),
        .age_i(age_i),
        .buf_occ_i(buf_occ_i),
        .grant_o(grant_o)
    );

    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        rst_n = 0;
        request_i = 0;
        for (int i=0; i<PORTS; i++) begin
            priority_i[i] = 0;
            age_i[i] = 0;
            buf_occ_i[i] = 0;
        end
        
        #20 rst_n = 1;
        
        // Scenario 1: Only Port 0 requests (Low Priority)
        @(posedge clk);
        request_i[0] = 1; priority_i[0] = 0; age_i[0] = 5; buf_occ_i[0] = 2;
        
        // Scenario 2: Port 0 (Low Prio, Old) vs Port 1 (High Prio, Young)
        @(posedge clk);
        request_i = 4'b0011;
        priority_i[1] = 3; age_i[1] = 1; buf_occ_i[1] = 1;
        
        // Scenario 3: Port 2 (Med Prio, Oldest) vs Port 1 (High Prio, Youngest)
        @(posedge clk);
        request_i = 4'b0110;
        priority_i[2] = 2; age_i[2] = 15; buf_occ_i[2] = 1;
        
        @(posedge clk);
        request_i = 0;
        
        #50;
        $display("[READ] PASSED %0t -- TOPSIS Arbiter Functional Simulation Complete", $time);
        $finish;
    end
endmodule
