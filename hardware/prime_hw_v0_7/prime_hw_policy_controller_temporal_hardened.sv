`timescale 1ns/1ps

module prime_hw_policy_controller_temporal_hardened (
    input  wire       clk,
    input  wire       reset_n,
    input  wire       boot_verified,
    input  wire       policy_valid,
    input  wire       health_degraded,
    input  wire       fatal_fault,
    input  wire       recovery_authorized,
    input  wire       request_valid,
    input  wire       request_authorized,
    input  wire       degraded_request_authorized,
    input  wire [7:0] command_seq,
    output wire       policy_allow,
    output wire       policy_deny,
    output wire       execute_pulse,
    output wire       command_denied,
    output wire       safe_state,
    output wire       state_integrity_fault,
    output wire       authorization_integrity_fault,
    output wire       authorization_fault_latched,
    output wire       temporal_integrity_fault,
    output wire       temporal_fault_latched,
    output wire       sequence_state_integrity_fault,
    output wire       fail_closed_active,
    output wire [2:0] state_code,
    output wire [7:0] expected_command_seq,
    output wire [7:0] expected_command_seq_inverse
);
    wire upstream_fail_closed_active;
    wire effective_fatal_fault;

    // Temporal faults are sticky and feed the inherited fatal path on the next
    // active edge. Immediate actuation denial is handled by the temporal guard,
    // so no unsafe pulse is allowed while semantic SAFE convergence occurs.
    assign effective_fatal_fault = fatal_fault || temporal_fault_latched;

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

    prime_hw_temporal_command_guard temporal_guard (
        .clk(clk),
        .reset_n(reset_n),
        .upstream_allow(policy_allow),
        .request_valid(request_valid),
        .command_seq(command_seq),
        .execute_pulse(execute_pulse),
        .temporal_integrity_fault(temporal_integrity_fault),
        .temporal_fault_latched(temporal_fault_latched),
        .sequence_state_integrity_fault(sequence_state_integrity_fault),
        .expected_command_seq(expected_command_seq),
        .expected_command_seq_inverse(expected_command_seq_inverse)
    );

    assign command_denied = request_valid && !execute_pulse;
    assign fail_closed_active =
        upstream_fail_closed_active ||
        temporal_integrity_fault ||
        temporal_fault_latched ||
        sequence_state_integrity_fault;
endmodule
