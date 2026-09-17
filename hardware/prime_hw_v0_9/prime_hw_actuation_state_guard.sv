`timescale 1ns/1ps

module prime_hw_actuation_state_guard (
    input  wire [83:0] state_primary,
    input  wire [83:0] state_inverse,
    output wire        state_valid,
    output wire        state_integrity_fault
);
    assign state_valid = (state_inverse == ~state_primary);
    assign state_integrity_fault = !state_valid;
endmodule
