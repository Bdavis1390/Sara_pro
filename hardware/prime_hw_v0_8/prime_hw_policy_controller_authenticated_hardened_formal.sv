`timescale 1ns/1ps

module prime_hw_policy_controller_authenticated_hardened_formal;
    (* gclk *) reg clk;

    (* anyseq *) reg reset_n;
    (* anyseq *) reg boot_verified;
    (* anyseq *) reg policy_valid;
    (* anyseq *) reg health_degraded;
    (* anyseq *) reg fatal_fault;
    (* anyseq *) reg recovery_authorized;
    (* anyseq *) reg request_valid;
    (* anyseq *) reg request_authorized;
    (* anyseq *) reg degraded_request_authorized;
    (* anyseq *) reg trusted_epoch_valid;
    (* anyseq *) reg [31:0] trusted_epoch;
    (* anyseq *) reg verifier_valid;
    (* anyseq *) reg [31:0] verified_epoch;
    (* anyseq *) reg [7:0] verified_seq;
    (* anyseq *) reg [63:0] verified_command_digest;
    (* anyseq *) reg [31:0] command_epoch;
    (* anyseq *) reg [7:0] command_seq;
    (* anyseq *) reg [63:0] command_digest;

    // Unconstrained standalone envelope-guard probe.
    (* anyseq *) reg probe_policy_allow;
    (* anyseq *) reg probe_request_valid;
    (* anyseq *) reg probe_trusted_epoch_valid;
    (* anyseq *) reg [31:0] probe_trusted_epoch;
    (* anyseq *) reg probe_verifier_valid;
    (* anyseq *) reg [31:0] probe_verified_epoch;
    (* anyseq *) reg [7:0] probe_verified_seq;
    (* anyseq *) reg [63:0] probe_verified_digest;
    (* anyseq *) reg [31:0] probe_command_epoch;
    (* anyseq *) reg [7:0] probe_command_seq;
    (* anyseq *) reg [63:0] probe_command_digest;
    (* anyseq *) reg probe_auth_fault_latched_in;

    // Independent sticky-latch probe.
    (* anyseq *) reg probe_fault_event;

    wire probe_binding_valid;
    wire probe_auth_fault;
    wire probe_authenticated_allow;
    wire probe_latch_state;

    wire policy_allow;
    wire policy_deny;
    wire authenticated_allow;
    wire execute_pulse;
    wire command_denied;
    wire envelope_binding_valid;
    wire authentication_integrity_fault;
    wire authentication_fault_latched;
    wire temporal_integrity_fault;
    wire temporal_fault_latched;
    wire sequence_state_integrity_fault;
    wire state_integrity_fault;
    wire authorization_integrity_fault;
    wire authorization_fault_latched;
    wire safe_state;
    wire fail_closed_active;
    wire [2:0] state_code;
    wire [7:0] expected_command_seq;
    wire [7:0] expected_command_seq_inverse;

    wire ref_policy_allow;
    wire ref_policy_deny;
    wire ref_execute_pulse;
    wire ref_command_denied;
    wire ref_safe_state;
    wire ref_state_integrity_fault;
    wire ref_authorization_integrity_fault;
    wire ref_authorization_fault_latched;
    wire ref_temporal_integrity_fault;
    wire ref_temporal_fault_latched;
    wire ref_sequence_state_integrity_fault;
    wire ref_fail_closed_active;
    wire [2:0] ref_state_code;
    wire [7:0] ref_expected_command_seq;
    wire [7:0] ref_expected_command_seq_inverse;

    localparam [2:0] ST_RESET       = 3'd0;
    localparam [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam [2:0] ST_VERIFY      = 3'd2;
    localparam [2:0] ST_OPERATIONAL = 3'd3;
    localparam [2:0] ST_DEGRADED    = 3'd4;
    localparam [2:0] ST_SAFE        = 3'd5;
    localparam [2:0] ST_RECOVERY    = 3'd6;

    reg past_valid = 1'b0;

    wire expected_probe_binding =
        probe_trusted_epoch_valid &&
        probe_verifier_valid &&
        (probe_command_epoch == probe_trusted_epoch) &&
        (probe_verified_epoch == probe_command_epoch) &&
        (probe_verified_seq == probe_command_seq) &&
        (probe_verified_digest == probe_command_digest);
    wire expected_probe_fault =
        probe_policy_allow && probe_request_valid && !expected_probe_binding;
    wire expected_probe_allow =
        probe_policy_allow &&
        probe_request_valid &&
        expected_probe_binding &&
        !probe_auth_fault_latched_in;

    prime_hw_policy_controller_authenticated_hardened dut (
        .clk(clk),
        .reset_n(reset_n),
        .boot_verified(boot_verified),
        .policy_valid(policy_valid),
        .health_degraded(health_degraded),
        .fatal_fault(fatal_fault),
        .recovery_authorized(recovery_authorized),
        .request_valid(request_valid),
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
        .policy_deny(policy_deny),
        .authenticated_allow(authenticated_allow),
        .execute_pulse(execute_pulse),
        .command_denied(command_denied),
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
        .fail_closed_active(fail_closed_active),
        .state_code(state_code),
        .expected_command_seq(expected_command_seq),
        .expected_command_seq_inverse(expected_command_seq_inverse)
    );

    // Exact v0.7 reference for the valid-envelope path.
    prime_hw_policy_controller_temporal_hardened reference_dut (
        .clk(clk),
        .reset_n(reset_n),
        .boot_verified(boot_verified),
        .policy_valid(policy_valid),
        .health_degraded(health_degraded),
        .fatal_fault(fatal_fault),
        .recovery_authorized(recovery_authorized),
        .request_valid(request_valid),
        .request_authorized(request_authorized),
        .degraded_request_authorized(degraded_request_authorized),
        .command_seq(command_seq),
        .policy_allow(ref_policy_allow),
        .policy_deny(ref_policy_deny),
        .execute_pulse(ref_execute_pulse),
        .command_denied(ref_command_denied),
        .safe_state(ref_safe_state),
        .state_integrity_fault(ref_state_integrity_fault),
        .authorization_integrity_fault(ref_authorization_integrity_fault),
        .authorization_fault_latched(ref_authorization_fault_latched),
        .temporal_integrity_fault(ref_temporal_integrity_fault),
        .temporal_fault_latched(ref_temporal_fault_latched),
        .sequence_state_integrity_fault(ref_sequence_state_integrity_fault),
        .fail_closed_active(ref_fail_closed_active),
        .state_code(ref_state_code),
        .expected_command_seq(ref_expected_command_seq),
        .expected_command_seq_inverse(ref_expected_command_seq_inverse)
    );

    prime_hw_authenticated_envelope_guard probe_guard (
        .policy_allow(probe_policy_allow),
        .request_valid(probe_request_valid),
        .trusted_epoch_valid(probe_trusted_epoch_valid),
        .trusted_epoch(probe_trusted_epoch),
        .verifier_valid(probe_verifier_valid),
        .verified_epoch(probe_verified_epoch),
        .verified_seq(probe_verified_seq),
        .verified_command_digest(probe_verified_digest),
        .command_epoch(probe_command_epoch),
        .command_seq(probe_command_seq),
        .command_digest(probe_command_digest),
        .authentication_fault_latched(probe_auth_fault_latched_in),
        .envelope_binding_valid(probe_binding_valid),
        .authentication_integrity_fault(probe_auth_fault),
        .authenticated_allow(probe_authenticated_allow)
    );

    prime_hw_authentication_fault_latch probe_latch (
        .clk(clk),
        .reset_n(reset_n),
        .authentication_integrity_fault(probe_fault_event),
        .authentication_fault_latched(probe_latch_state)
    );

    always @(posedge clk) begin
        past_valid <= 1'b1;

        if (!past_valid)
            assume(!reset_n);
        else
            assume(reset_n);

        // Complete symbolic guard predicate over unconstrained epoch/sequence/digest.
        assert(probe_binding_valid == expected_probe_binding);
        assert(probe_auth_fault == expected_probe_fault);
        assert(probe_authenticated_allow == expected_probe_allow);
        if (probe_authenticated_allow) begin
            assert(probe_binding_valid);
            assert(!probe_auth_fault);
            assert(!probe_auth_fault_latched_in);
        end
        if (probe_auth_fault_latched_in)
            assert(!probe_authenticated_allow);

        // The differential path models a valid external trust contract. This is
        // an assumption about the verifier/epoch root, not a proof of them.
        if (past_valid) begin
            assume(trusted_epoch_valid);
            assume(verifier_valid);
            assume(command_epoch == trusted_epoch);
            assume(verified_epoch == command_epoch);
            assume(verified_seq == command_seq);
            assume(verified_command_digest == command_digest);

            assert(envelope_binding_valid);
            assert(!authentication_integrity_fault);
            assert(!authentication_fault_latched);

            // With exact authenticated binding, v0.8 preserves v0.7 behavior.
            assert(policy_allow == ref_policy_allow);
            assert(policy_deny == ref_policy_deny);
            assert(execute_pulse == ref_execute_pulse);
            assert(command_denied == ref_command_denied);
            assert(safe_state == ref_safe_state);
            assert(state_integrity_fault == ref_state_integrity_fault);
            assert(authorization_integrity_fault == ref_authorization_integrity_fault);
            assert(authorization_fault_latched == ref_authorization_fault_latched);
            assert(temporal_integrity_fault == ref_temporal_integrity_fault);
            assert(temporal_fault_latched == ref_temporal_fault_latched);
            assert(sequence_state_integrity_fault == ref_sequence_state_integrity_fault);
            assert(state_code == ref_state_code);
            assert(expected_command_seq == ref_expected_command_seq);
            assert(expected_command_seq_inverse == ref_expected_command_seq_inverse);

            if (execute_pulse) begin
                assert(policy_allow);
                assert(authenticated_allow);
                assert(envelope_binding_valid);
                assert(command_epoch == trusted_epoch);
                assert(verified_epoch == command_epoch);
                assert(verified_seq == command_seq);
                assert(verified_command_digest == command_digest);
                assert(command_seq == expected_command_seq);
            end

            if ($past(reset_n) && $past(probe_latch_state))
                assert(probe_latch_state);
            if ($past(reset_n) && $past(probe_fault_event))
                assert(probe_latch_state);
        end

        // Seven semantic states plus nine authenticated-envelope witnesses = 16.
        cover(state_code == ST_RESET);
        cover(state_code == ST_BOOT_LOCKED);
        cover(state_code == ST_VERIFY);
        cover(state_code == ST_OPERATIONAL);
        cover(state_code == ST_DEGRADED);
        cover(state_code == ST_SAFE);
        cover(state_code == ST_RECOVERY);
        cover(execute_pulse);
        cover(probe_authenticated_allow);
        cover(probe_policy_allow && probe_request_valid && !probe_trusted_epoch_valid && probe_auth_fault);
        cover(probe_policy_allow && probe_request_valid && probe_trusted_epoch_valid && !probe_verifier_valid && probe_auth_fault);
        cover(probe_policy_allow && probe_request_valid && probe_trusted_epoch_valid && probe_verifier_valid && (probe_command_epoch != probe_trusted_epoch) && probe_auth_fault);
        cover(probe_policy_allow && probe_request_valid && probe_trusted_epoch_valid && probe_verifier_valid && (probe_verified_epoch != probe_command_epoch) && probe_auth_fault);
        cover(probe_policy_allow && probe_request_valid && probe_trusted_epoch_valid && probe_verifier_valid && (probe_verified_seq != probe_command_seq) && probe_auth_fault);
        cover(probe_policy_allow && probe_request_valid && probe_trusted_epoch_valid && probe_verifier_valid && (probe_verified_digest != probe_command_digest) && probe_auth_fault);
        cover(probe_latch_state);
    end
endmodule
