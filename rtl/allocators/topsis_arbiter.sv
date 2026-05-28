`timescale 1ns / 1ps

module topsis_arbiter #(
    parameter PORTS = 4,
    parameter WEIGHT_PRIO = 4'd8,
    parameter WEIGHT_AGE  = 4'd4,
    parameter WEIGHT_BUF  = 4'd2
)(
    input  logic             clk,
    input  logic             rst_n,
    input  logic [PORTS-1:0] request_i,
    input  logic [1:0]       priority_i [PORTS-1:0],
    input  logic [3:0]       age_i [PORTS-1:0],
    input  logic [3:0]       buf_occ_i [PORTS-1:0],
    output logic [PORTS-1:0] grant_o
);

    logic [15:0] scores [PORTS-1:0];
    logic [15:0] min_score;
    logic [PORTS-1:0] grant_mask;

    // Simplified Euclidean Distance proxy calculation (lower score is better)
    // Score = (Ideal_Priority - Priority)*W_Prio + (Ideal_Age - Age)*W_Age + (Buf_Occ)*W_Buf
    // Assuming Ideal_Priority = 3 (highest), Ideal_Age = 15 (oldest)
    genvar i;
    generate
        for (i = 0; i < PORTS; i++) begin : gen_scores
            always_comb begin
                if (request_i[i]) begin
                    scores[i] = ((3 - priority_i[i]) * WEIGHT_PRIO) + 
                                ((15 - age_i[i]) * WEIGHT_AGE) + 
                                (buf_occ_i[i] * WEIGHT_BUF);
                end else begin
                    scores[i] = 16'hFFFF; // Max score for non-requesters
                end
            end
        end
    endgenerate

    // Find the minimum score (best candidate)
    always_comb begin
        min_score = 16'hFFFF;
        grant_mask = '0;
        
        for (int j = 0; j < PORTS; j++) begin
            if (request_i[j] && scores[j] <= min_score) begin
                min_score = scores[j];
            end
        end
        
        // Strict priority resolution in case of score ties
        for (int k = 0; k < PORTS; k++) begin
            if (request_i[k] && scores[k] == min_score) begin
                grant_mask[k] = 1'b1;
                break; // Grant only the first matching port
            end
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant_o <= '0;
        end else begin
            grant_o <= grant_mask;
        end
    end

    // SystemVerilog Assertion (SVA) for SymbiYosys/JasperGold
    // Property: A high priority request (priority 3) should never starve.
    `ifdef FORMAL
    property p_no_starvation;
        @(posedge clk) disable iff (!rst_n)
        (request_i[0] && priority_i[0] == 3) |-> s_eventually (grant_o[0]);
    endproperty
    assert property(p_no_starvation);
    `endif

endmodule
