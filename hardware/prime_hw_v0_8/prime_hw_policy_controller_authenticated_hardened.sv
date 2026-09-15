`timescale 1ns/1ps

module prime_hw_policy_controller_authenticated_hardened (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        boot_verified,
    input  wire        policy_valid,
    input  wire        health_degraded,
    input  wire        fatal_fault,
    input  wire        recovery_authorized,
    input  wire        request_valid,
    input  wire        request_authorized,
    input  wire        degraded_request_authorized,
    input  wire        trusted_epoch_valid,
    input  wire [31:0] trusted_epoch,
    input  wire        verifier_valid,
    input  wire [31:0] verified_epoch,
    input  wire [7:0]  verified_seq,
    input  wire [63:0] verified_command_digest,
    input  wire [31:0] command_epoch,
    input  wire [7:0]  command_seq,
    input  wire [63:0] command_digest,
    output wire        policy_allow,
    output wire        policy_deny,
    output wire        authenticated_allow,
    output wire        execute_pulse,
    output wire        command_denied,
    output wire        envelope_binding_valid,
    output wire        authentication_integrity_fault,
    output wire        authentication_fault_latched,
    output wire        temporal_integrity_fault,
    output wire        temporal_fault_latched,
    output wire        sequence_state_integrity_fault,
    output wire        state_integrity_fault,
    output wire        authorization_integrity_fault,
    output wire        authorization_fault_latched,
    output wire        safe_state,
    output wire        fail_closed_active,
    output wire [2:0]  state_code,
    output wire [7:0]  expected_command_seq,
    output wire [7:0]  expected_command_seq_inverse
);
    wire upstream_fail_closed_active;
    wire effective_fatal_fault;

    (* keep *) wire authenticated_allow_q;
    (* keep *) wire authentication_fault_latched_q;

    assign effective_fatal_fault =
        fatal_fault || authentication_fault_latched_q || temporal_fault_latched;

    // v0.6 remains the policy/authorization core. Authentication and temporal
    // integrity are independent downstream prerequisites for actuation.
    prime_hw_policy_controller_authorization_hardened authorization_core (
        .clk(clk),
        .reset_n(reset_n),
        .boot_verified(boot_verified),
        .policy_valid(policy_valid),
        .health_degraded(health_degraded),
        .fatal_fault(effective_fatal_fault),
        .recovery_authorized(recovery_authorized),
        .request_valid(request_valid),
        .request_authorized(request_authorized),
        .degraded_request_authorized(degraded_request_authorized),
        .allow(policy_allow),
        .deny(policy_deny),
        .safe_state(safe_state),
        .state_integrity_fault(state_integrity_fault),
        .authorization_integrity_fault(authorization_integrity_fault),
        .authorization_fault_latched(authorization_fault_latched),
        .fail_closed_active(upstream_fail_closed_active),
        .state_code(state_code)
    );

    prime_hw_authenticated_envelope_guard envelope_guard (
        .policy_allow(policy_allow),
        .request_valid(request_valid),
        .trusted_epoch_valid(trusted_epoch_valid),
        .trusted_epoch(trusted_epoch),
        .verifier_valid(verifier_valid),
        .verified_epoch(verified_epoch),
        .verified_seq(verified_seq),
        .verified_command_digest(verified_command_digest),
        .command_epoch(command_epoch),
        .command_seq(command_seq),
        .command_digest(command_digest),
        .authentication_fault_latched(authentication_fault_latched_q),
        .envelope_binding_valid(envelope_binding_valid),
        .authentication_integrity_fault(authentication_integrity_fault),
        .authenticated_allow(authenticated_allow_q)
    );

    prime_hw_authentication_fault_latch authentication_latch (
        .clk(clk),
        .reset_n(reset_n),
        .authentication_integrity_fault(authentication_integrity_fault),
        .authentication_fault_latched(authentication_fault_latched_q)
    );

    // The authenticated authorization is then consumed by the exact v0.7
    // temporal gate. Authentication failure cannot advance temporal state.
    prime_hw_temporal_command_guard temporal_guard (
        .clk(clk),
        .reset_n(reset_n),
        .upstream_allow(authenticated_allow_q),
        .request_valid(request_valid),
        .command_seq(command_seq),
        .execute_pulse(execute_pulse),
        .temporal_integrity_fault(temporal_integrity_fault),
        .temporal_fault_latched(temporal_fault_latched),
        .sequence_state_integrity_fault(sequence_state_integrity_fault),
        .expected_command_seq(expected_command_seq),
        .expected_command_seq_inverse(expected_command_seq_inverse)
    );

    assign authenticated_allow = authenticated_allow_q;
    assign authentication_fault_latched = authentication_fault_latched_q;
    assign command_denied = request_valid && !execute_pulse;

    assign fail_closed_active =
        upstream_fail_closed_active ||
        authentication_integrity_fault ||
        authentication_fault_latched_q ||
        temporal_integrity_fault ||
        temporal_fault_latched ||
        sequence_state_integrity_fault;
endmodule
