`timescale 1ns/1ps

module prime_hw_authorization_voter (
    input  logic core_allow_vote,
    input  logic core_deny_vote,
    input  logic witness_allow_vote,
    input  logic witness_deny_vote,
    input  logic request_valid,
    input  logic state_integrity_fault,
    input  logic authorization_fault_latched,
    output logic authorization_integrity_fault,
    output logic allow,
    output logic deny
);
    always_comb begin
        authorization_integrity_fault =
            (core_allow_vote != witness_allow_vote) ||
            (core_deny_vote != witness_deny_vote);

        // Unsafe authorization requires affirmative agreement from both paths,
        // no state-integrity fault, no authorization disagreement, and no prior
        // sticky authorization-integrity event.
        allow =
            request_valid &&
            core_allow_vote &&
            witness_allow_vote &&
            !state_integrity_fault &&
            !authorization_integrity_fault &&
            !authorization_fault_latched;

        // Denial is recomputed after voting. A disagreement can therefore only
        // remove permission, never create permission, in the declared model.
        deny = request_valid && !allow;
    end
endmodule
