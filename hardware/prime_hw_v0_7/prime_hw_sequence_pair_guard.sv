`timescale 1ns/1ps

module prime_hw_sequence_pair_guard (
    input  wire [7:0] expected_seq_primary,
    input  wire [7:0] expected_seq_inverse,
    output wire       sequence_state_valid,
    output wire       sequence_state_integrity_fault
);
    assign sequence_state_valid = (expected_seq_inverse == ~expected_seq_primary);
    assign sequence_state_integrity_fault = !sequence_state_valid;
endmodule
