`timescale 1ns/1ps

module prime_hw_authorization_witness (
    input  logic [2:0] state_code,
    input  logic       state_integrity_fault,
    input  logic       boot_verified,
    input  logic       policy_valid,
    input  logic       health_degraded,
    input  logic       fatal_fault,
    input  logic       request_valid,
    input  logic       request_authorized,
    input  logic       degraded_request_authorized,
    output logic       allow_vote,
    output logic       deny_vote
);
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;
    localparam logic [2:0] ST_DEGRADED    = 3'd4;

    logic trusted;
    logic ordinary_path;
    logic degraded_path;

    // Intentionally expressed as a direct Boolean predicate rather than the
    // case-structured output logic used by the controller implementation.
    always_comb begin
        trusted = boot_verified && policy_valid && !fatal_fault && !state_integrity_fault;

        ordinary_path =
            (state_code == ST_OPERATIONAL) &&
            !health_degraded &&
            request_authorized;

        degraded_path =
            (state_code == ST_DEGRADED) &&
            degraded_request_authorized;

        allow_vote = request_valid && trusted && (ordinary_path || degraded_path);
        deny_vote = request_valid && !allow_vote;
    end
endmodule
