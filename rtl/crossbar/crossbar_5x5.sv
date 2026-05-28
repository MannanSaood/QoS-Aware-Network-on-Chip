module crossbar_5x5 #(
    parameter FLIT_WIDTH = 34
)(
    input  logic [FLIT_WIDTH-1:0] data_i [4:0],
    input  logic [4:0]            sel_i  [4:0], // One-hot select for each output port
    output logic [FLIT_WIDTH-1:0] data_o [4:0]
);

    genvar out_port;
    generate
        for (out_port = 0; out_port < 5; out_port++) begin : gen_mux
            always_comb begin
                data_o[out_port] = '0;
                for (int in_port = 0; in_port < 5; in_port++) begin
                    if (sel_i[out_port][in_port]) begin
                        data_o[out_port] = data_i[in_port];
                    end
                end
            end
        end
    endgenerate

endmodule
