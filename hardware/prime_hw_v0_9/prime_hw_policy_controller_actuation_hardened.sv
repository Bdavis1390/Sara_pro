`timescale 1ns/1ps

module prime_hw_policy_controller_actuation_hardened #(
    parameter integer ACK_TIMEOUT_CYCLES = 16
) (
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
    input  wire        actuator_ack_valid,
    input  wire        actuator_ack_success,
    input  wire [7:0]  actuator_ack_seq,
    input  wire [63:0] actuator_ack_digest,
    output wire        command_ready,
    output wire        policy_allow,
    output wire        authenticated_allow,
    output wire        temporal_execute_pulse,
    output wire        actuator_issue_pulse,
    output wire        actuator_commit_pulse,
    output wire        command_denied,
    output wire        actuation_pending,
    output wire [7:0]  pending_seq,
    output wire [63:0] pending_digest,
    output wire [7:0]  pending_age,
    output wire        actuation_integrity_fault,
    output wire        actuation_fault_latched,
    output wire        bridge_state_integrity_fault,
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
    wire gated_request_valid;
    wire upstream_protocol_violation;
    wire effective_fatal_fault;
    wire upstream_policy_deny;
    wire upstream_command_denied;
    wire upstream_fail_closed_active;

    // A new command may enter the authenticated/temporal pipeline only while the
    // actuation bridge has no unresolved transaction, no fault, and no concurrent
    // acknowledgement. This prevents temporal sequence consumption ahead of the
    // downstream commit boundary.
    assign command_ready =
        !actuation_pending &&
        !actuation_fault_latched &&
        !bridge_state_integrity_fault &&
        !actuator_ack_valid;

    assign gated_request_valid = request_valid && command_ready;
    assign upstream_protocol_violation = request_valid && !command_ready;
    assign effective_fatal_fault = fatal_fault || actuation_fault_latched;

    prime_hw_policy_controller_authenticated_hardened authenticated_core (
        .clk(clk),
        .reset_n(reset_n),
        .boot_verified(boot_verified),
        .policy_valid(policy_valid),
        .health_degraded(health_degraded),
        .fatal_fault(effective_fatal_fault),
        .recovery_authorized(recovery_authorized),
        .request_valid(gated_request_valid),
        .request_authorized(request_authorized),
        .degraded_request_authorized(degraded_request_authorized),
        .trusted_epoch_valid(trusted_epoch_valid),
        .trusted_epoch(trusted_epoch),
        .verifier_valid(verifier_valid),
        .verified_epoch(verified_epoch),
        .verified_seq(verified_seq),
        .verified_command_digest(verified_command_digest),
        .command_epoch(command_epoch),
        .command_seq(command_seq),
        .command_digest(command_digest),
        .policy_allow(policy_allow),
        .policy_deny(upstream_policy_deny),
        .authenticated_allow(authenticated_allow),
        .execute_pulse(temporal_execute_pulse),
        .command_denied(upstream_command_denied),
        .envelope_binding_valid(envelope_binding_valid),
        .authentication_integrity_fault(authentication_integrity_fault),
        .authentication_fault_latched(authentication_fault_latched),
        .temporal_integrity_fault(temporal_integrity_fault),
        .temporal_fault_latched(temporal_fault_latched),
        .sequence_state_integrity_fault(sequence_state_integrity_fault),
        .state_integrity_fault(state_integrity_fault),
        .authorization_integrity_fault(authorization_integrity_fault),
        .authorization_fault_latched(authorization_fault_latched),
        .safe_state(safe_state),
        .fail_closed_active(upstream_fail_closed_active),
        .state_code(state_code),
        .expected_command_seq(expected_command_seq),
        .expected_command_seq_inverse(expected_command_seq_inverse)
    );

    prime_hw_actuation_commit_bridge #(
        .ACK_TIMEOUT_CYCLES(ACK_TIMEOUT_CYCLES)
    ) actuation_bridge (
        .clk(clk),
        .reset_n(reset_n),
        .upstream_execute_pulse(temporal_execute_pulse),
        .upstream_protocol_violation(upstream_protocol_violation),
        .command_seq(command_seq),
        .command_digest(command_digest),
        .actuator_ack_valid(actuator_ack_valid),
        .actuator_ack_success(actuator_ack_success),
        .actuator_ack_seq(actuator_ack_seq),
        .actuator_ack_digest(actuator_ack_digest),
        .actuator_issue_pulse(actuator_issue_pulse),
        .actuator_commit_pulse(actuator_commit_pulse),
        .actuation_pending(actuation_pending),
        .pending_seq(pending_seq),
        .pending_digest(pending_digest),
        .pending_age(pending_age),
        .actuation_integrity_fault(actuation_integrity_fault),
        .actuation_fault_latched(actuation_fault_latched),
        .bridge_state_integrity_fault(bridge_state_integrity_fault)
    );

    // Raw ingress semantics: a request is denied unless it actually reaches the
    // one-cycle digital actuator-issue boundary. This does not claim physical
    // motion or physical exactly-once behavior.
    assign command_denied = request_valid && !actuator_issue_pulse;

    assign fail_closed_active =
        upstream_fail_closed_active ||
        upstream_protocol_violation ||
        actuation_integrity_fault ||
        actuation_fault_latched ||
        bridge_state_integrity_fault;
endmodule
