`timescale 1ns/1ps

module prime_hw_authenticated_envelope_guard (
    input  wire        policy_allow,
    input  wire        request_valid,
    input  wire        trusted_epoch_valid,
    input  wire [31:0] trusted_epoch,
    input  wire        verifier_valid,
    input  wire [31:0] verified_epoch,
    input  wire [7:0]  verified_seq,
    input  wire [63:0] verified_command_digest,
    input  wire [31:0] command_epoch,
    input  wire [7:0]  command_seq,
    input  wire [63:0] command_digest,
    input  wire        authentication_fault_latched,
    output wire        envelope_binding_valid,
    output wire        authentication_integrity_fault,
    output wire        authenticated_allow
);
    wire exact_epoch_binding;
    wire exact_command_binding;

    // trusted_epoch_* and verifier_* are external trust inputs. This module
    // enforces exact binding to them; it does not establish their authenticity,
    // monotonicity, nonvolatile retention, or cryptographic correctness.
    assign exact_epoch_binding =
        trusted_epoch_valid &&
        verifier_valid &&
        (command_epoch == trusted_epoch) &&
        (verified_epoch == command_epoch);

    assign exact_command_binding =
        (verified_seq == command_seq) &&
        (verified_command_digest == command_digest);

    assign envelope_binding_valid = exact_epoch_binding && exact_command_binding;

    // A policy-approved active request without exact authenticated binding is a
    // security/control-integrity event and is latched by the surrounding wrapper.
    assign authentication_integrity_fault =
        policy_allow && request_valid && !envelope_binding_valid;

    assign authenticated_allow =
        policy_allow &&
        request_valid &&
        envelope_binding_valid &&
        !authentication_fault_latched;
endmodule
