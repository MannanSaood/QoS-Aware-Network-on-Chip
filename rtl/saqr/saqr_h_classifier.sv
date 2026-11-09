// SAQR-H source classifier (docs/SAQR_SPEC_V2.md §19-§20), one per network interface.
// Cycle-level RTL of algorithms/saqr_hot/routing.hpp (saqr_hot_classify):
//   SAQR-SC: last-M destination history + 8.8 repeat-rate EWMA + hysteresis bit;
//   SAQR-H : hot-destination candidate + 12-bit share EWMA + hysteresis bit;
//   mark   : SAQR-SC bit OR tracker bit, produced for every injected packet (in_valid),
//            registered with the packet header (1 header bit).
// Equivalence with the C++ model is checked by tests/rtl/saqr_h_classifier_tb.sv
// against vectors written by tests/rtl/saqr_h_vectors.cpp.
module saqr_h_classifier #(
    parameter int DW        = 10,    // destination id width (k = 32: 1024 nodes)
    parameter int M         = 4,     // history depth
    parameter int SC_ON     = 128,   // SAQR-SC thresholds (x/256)
    parameter int SC_OFF    = 64,
    parameter int SC_SHIFT  = 4,
    parameter int HOT_EN    = 1,     // 0: SAQR-SC only
    parameter int HOT_ON    = 451,   // tracker thresholds (x/4096)
    parameter int HOT_OFF   = 328,
    parameter int HOT_FLOOR = 205,
    parameter int HOT_INIT  = 410,
    parameter int HOT_SHIFT = 4
) (
    input  logic          clk,
    input  logic          rst_n,
    input  logic          in_valid,     // one packet injected this cycle
    input  logic [DW-1:0] in_dest,
    output logic          mark          // header bit for this packet (valid with in_valid)
);
    // ---- SAQR-SC state ----
    logic [DW-1:0] hist [M];
    logic [$clog2(M+1)-1:0] fill;
    logic [$clog2(M)-1:0]   head;
    logic signed [10:0] ewma;           // 0..256
    logic sc_bit;
    // ---- tracker state ----
    logic [DW-1:0] cand;
    logic          cand_valid;
    logic signed [13:0] f;              // 0..4096
    logic hot_bit;

    // History hit (before recording in_dest).
    logic hit;
    always_comb begin
        hit = 1'b0;
        for (int i = 0; i < M; i++) if (i < fill && hist[i] == in_dest) hit = 1'b1;
    end

    // SAQR-SC next state.
    logic signed [11:0] sc_step;
    logic signed [11:0] ewma_n;
    logic sc_n;
    always_comb begin
        sc_step = ((hit ? 12'sd256 : 12'sd0) - ewma) >>> SC_SHIFT;
        ewma_n  = ewma + sc_step;
        if (ewma_n < 0) ewma_n = 0;
        sc_n = sc_bit;
        if (!sc_bit && ewma_n >= SC_ON) sc_n = 1'b1;
        else if (sc_bit && ewma_n < SC_OFF) sc_n = 1'b0;
    end

    // Tracker next state.
    logic signed [14:0] f_n;
    logic [DW-1:0] cand_n;
    logic cand_valid_n;
    logic hot_n;
    logic is_cand;
    always_comb begin
        is_cand = cand_valid && (cand == in_dest);
        if (is_cand) f_n = f + ((15'sd4096 - f) >>> HOT_SHIFT);
        else         f_n = f - (f >>> HOT_SHIFT);
        cand_n = cand; cand_valid_n = cand_valid;
        if (f_n < HOT_FLOOR && hit && !is_cand) begin cand_n = in_dest; cand_valid_n = 1'b1; f_n = HOT_INIT; end
        hot_n = hot_bit;
        if (!hot_bit && f_n >= HOT_ON) hot_n = 1'b1;
        else if (hot_bit && f_n < HOT_OFF) hot_n = 1'b0;
    end

    assign mark = sc_n | (HOT_EN != 0 ? hot_n : 1'b0);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < M; i++) hist[i] <= '0;
            fill <= '0; head <= '0; ewma <= '0; sc_bit <= 1'b0;
            cand <= '0; cand_valid <= 1'b0; f <= '0; hot_bit <= 1'b0;
        end else if (in_valid) begin
            hist[head] <= in_dest;
            head <= (head == M-1) ? '0 : head + 1'b1;
            if (fill < M) fill <= fill + 1'b1;
            ewma <= ewma_n[10:0]; sc_bit <= sc_n;
            if (HOT_EN != 0) begin
                f <= f_n[13:0]; cand <= cand_n; cand_valid <= cand_valid_n; hot_bit <= hot_n;
            end
        end
    end
endmodule
