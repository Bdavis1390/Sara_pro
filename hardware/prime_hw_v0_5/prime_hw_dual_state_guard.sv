`timescale 1ns/1ps

module prime_hw_dual_state_guard (
    input  logic [7:0] primary_state,
    input  logic [6:0] shadow_state,
    output logic       primary_valid,
    output logic       shadow_valid,
    output logic       state_integrity_fault,
    output logic [2:0] semantic_state
);
    localparam logic [2:0] ST_SAFE = 3'd5;

    logic [2:0] primary_semantic;
    logic [2:0] shadow_semantic;

    prime_hw_state_code_guard primary_guard (
        .encoded_state(primary_state),
        .state_valid(primary_valid),
        .semantic_state(primary_semantic)
    );

    prime_hw_shadow_state_guard shadow_guard (
        .shadow_state(shadow_state),
        .shadow_valid(shadow_valid),
        .semantic_state(shadow_semantic)
    );

    always_comb begin
        state_integrity_fault =
            !primary_valid || !shadow_valid || (primary_semantic != shadow_semantic);
        semantic_state = state_integrity_fault ? ST_SAFE : primary_semantic;
    end
endmodule
