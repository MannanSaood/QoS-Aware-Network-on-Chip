import noc_params::*;

module circular_buffer #(
    parameter BUFFER_SIZE = 8
)(
    input flit_novc_t data_i,
    input read_i,
    input write_i,
    input rst,
    input clk,
    output flit_novc_t data_o,
    output logic is_full_o,
    output logic is_empty_o,
    output logic credit_return_o
);

    localparam [31:0] POINTER_SIZE = $clog2(BUFFER_SIZE);

    flit_novc_t memory[BUFFER_SIZE-1:0];

    logic [POINTER_SIZE-1:0] read_ptr, read_ptr_next;
    logic [POINTER_SIZE-1:0] write_ptr, write_ptr_next;
    logic is_full_next, is_empty_next;
    logic [POINTER_SIZE:0] num_flits, num_flits_next;
    
    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            read_ptr    <= 0;
            write_ptr   <= 0;
            num_flits   <= 0;
            is_full_o   <= 0;
            is_empty_o  <= 1;
            credit_return_o <= 0;
        end else begin
            read_ptr    <= read_ptr_next;
            write_ptr   <= write_ptr_next;
            num_flits   <= num_flits_next;
            is_full_o   <= is_full_next;
            is_empty_o  <= is_empty_next;
            
            // Generate a credit return pulse when a flit is successfully read out
            credit_return_o <= (read_i & ~is_empty_o);

            if((~read_i & write_i & ~is_full_o) | (read_i & write_i))
                memory[write_ptr] <= data_i;
        end
    end

    always_comb begin
        data_o = memory[read_ptr];
        if (read_i & ~write_i & ~is_empty_o) begin
            read_ptr_next = increase_ptr(read_ptr);
            write_ptr_next = write_ptr;
            is_full_next = 0;
            is_empty_next = (read_ptr_next == write_ptr);
            num_flits_next = num_flits - 1;
        end else if (~read_i & write_i & ~is_full_o) begin
            read_ptr_next = read_ptr;
            write_ptr_next = increase_ptr(write_ptr);
            is_full_next = (write_ptr_next == read_ptr);
            is_empty_next = 0;
            num_flits_next = num_flits + 1;
        end else if (read_i & write_i & ~is_empty_o) begin
            read_ptr_next = increase_ptr(read_ptr);
            write_ptr_next = increase_ptr(write_ptr);
            is_full_next = is_full_o;
            is_empty_next = is_empty_o;
            num_flits_next = num_flits;
        end else begin
            read_ptr_next = read_ptr;
            write_ptr_next = write_ptr;
            is_full_next = is_full_o;
            is_empty_next = is_empty_o;
            num_flits_next = num_flits;
        end
    end

    function logic [POINTER_SIZE-1:0] increase_ptr (input logic [POINTER_SIZE-1:0] ptr);
        return (ptr == BUFFER_SIZE-1) ? 0 : ptr + 1;
    endfunction

endmodule