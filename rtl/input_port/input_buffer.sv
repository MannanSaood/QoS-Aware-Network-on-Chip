import noc_params::*;

module input_buffer #(
    parameter BUFFER_SIZE = 8
)(
    input flit_t data_i,
    input logic write_i,
    input logic [VC_NUM-1:0] read_i,
    input rst,
    input clk,
    
    output flit_novc_t data_o [VC_NUM-1:0],
    output logic [VC_NUM-1:0] is_full_o,
    output logic [VC_NUM-1:0] is_empty_o,
    output logic [VC_NUM-1:0] credit_return_o
);

    logic [VC_NUM-1:0] vc_write_en;

    // Demux the incoming write based on the VC identifier in the flit payload
    // Flit[31:30] represents Priority Class/VC (00: VC0, 01: VC1, 10: VC2, 11: VC3)
    always_comb begin
        vc_write_en = '0;
        if (write_i) begin
            // We assume data_i is the full flit and bits [31:30] are VC identifier
            case (data_i[31:30])
                2'b00: vc_write_en[0] = 1'b1;
                2'b01: vc_write_en[1] = 1'b1;
                2'b10: vc_write_en[2] = 1'b1;
                2'b11: vc_write_en[3] = 1'b1;
            endcase
        end
    end

    genvar i;
    generate
        for (i = 0; i < VC_NUM; i++) begin : gen_vc_buffers
            circular_buffer #(
                .BUFFER_SIZE(BUFFER_SIZE)
            ) vc_buf (
                .data_i(data_i[29:0]), // Payload without VC ID (simplified for this module)
                .read_i(read_i[i]),
                .write_i(vc_write_en[i]),
                .rst(rst),
                .clk(clk),
                .data_o(data_o[i]),
                .is_full_o(is_full_o[i]),
                .is_empty_o(is_empty_o[i]),
                .credit_return_o(credit_return_o[i])
            );
        end
    endgenerate

endmodule