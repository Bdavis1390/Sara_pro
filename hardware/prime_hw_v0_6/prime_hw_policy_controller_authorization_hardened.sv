`timescale 1ns/1ps

module prime_hw_policy_controller_authorization_hardened (
    input  logic       clk,
    input  logic       reset_n,
    input  logic       boot_verified,
    input  logic       policy_valid,
    input  logic       health_degraded,
    input  logic       fatal_fault,
    input  logic       recovery_authorized,
    input  logic       request_valid,
    input  logic       request_authorized,
    input  logic       degraded_request_authorized,
    output logic       allow,
    output logic       deny,
    output logic       safe_state,
    output logic       state_integrity_fault,
    output logic       authorization_integrity_fault,
    output logic       authorization_fault_latched,
    output logic       fail_closed_active,
    output logic [2:0] state_code
);
    logic core_allow_raw;
    logic core_deny_raw;
    logic core_safe_state;
    logic core_state_integrity_fault;
    logic [2:0] core_state_code;

    logic witness_allow_raw;
    logic witness_deny_raw;
    logic effective_fatal_fault;

    // These vote rails are preserved for post-elaboration structural evidence.
    // Preservation in the Yosys evidence netlist is not a physical-routing or
    // placement-separation claim.
    (* keep *) logic core_allow_vote;
    (* keep *) logic core_deny_vote;
    (* keep *) logic witness_allow_vote;
    (* keep *) logic witness_deny_vote;
    (* keep *) logic authorization_fault_latched_q;

    assign effective_fatal_fault = fatal_fault || authorization_fault_latched_q;

    // Primary authorization path: inherited v0.5 controller output logic.
    prime_hw_policy_controller_diverse core (
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
        .allow(core_allow_raw),
        .deny(core_deny_raw),
        .safe_state(core_safe_state),
        .state_integrity_fault(core_state_integrity_fault),
        .state_code(core_state_code)
    );

    // Independent authorization path: direct Boolean witness over the semantic
    // state and policy inputs rather than the core's case-structured output path.
    prime_hw_authorization_witness witness (
        .state_code(core_state_code),
        .state_integrity_fault(core_state_integrity_fault),
        .boot_verified(boot_verified),
        .policy_valid(policy_valid),
        .health_degraded(health_degraded),
        .fatal_fault(effective_fatal_fault),
        .request_valid(request_valid),
        .request_authorized(request_authorized),
        .degraded_request_authorized(degraded_request_authorized),
        .allow_vote(witness_allow_raw),
        .deny_vote(witness_deny_raw)
    );

    assign core_allow_vote = core_allow_raw;
    assign core_deny_vote = core_deny_raw;
    assign witness_allow_vote = witness_allow_raw;
    assign witness_deny_vote = witness_deny_raw;

    prime_hw_authorization_fault_latch fault_latch (
        .clk(clk),
        .reset_n(reset_n),
        .authorization_integrity_fault(authorization_integrity_fault),
        .authorization_fault_latched(authorization_fault_latched_q)
    );

    prime_hw_authorization_voter voter (
        .core_allow_vote(core_allow_vote),
        .core_deny_vote(core_deny_vote),
        .witness_allow_vote(witness_allow_vote),
        .witness_deny_vote(witness_deny_vote),
        .request_valid(request_valid),
        .state_integrity_fault(core_state_integrity_fault),
        .authorization_fault_latched(authorization_fault_latched_q),
        .authorization_integrity_fault(authorization_integrity_fault),
        .allow(allow),
        .deny(deny)
    );

    assign safe_state = core_safe_state;
    assign state_integrity_fault = core_state_integrity_fault;
    assign authorization_fault_latched = authorization_fault_latched_q;
    assign state_code = core_state_code;

    assign fail_closed_active =
        core_safe_state ||
        core_state_integrity_fault ||
        authorization_integrity_fault ||
        authorization_fault_latched_q;
endmodule
