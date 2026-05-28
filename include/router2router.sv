import noc_params::*;

interface router2router;

    flit_t data;
    logic is_valid;
    // TOPSIS Architecture updates: Replaced ON/OFF with credit returns per VC
    logic [VC_NUM-1:0] credit_return;
    logic [VC_NUM-1:0] is_allocatable;

    modport upstream (
        output data,
        output is_valid,
        input credit_return,
        input is_allocatable
    );

    modport downstream (
        input data,
        input is_valid,
        output credit_return,
        output is_allocatable
    );

endinterface