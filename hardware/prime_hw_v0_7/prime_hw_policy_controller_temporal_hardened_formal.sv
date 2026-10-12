`timescale 1ns/1ps

module prime_hw_policy_controller_temporal_hardened_formal;
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
    (* anyseq *) reg [7:0] command_seq;

    // Independent temporal-guard probe with unconstrained traffic.
    (* anyseq *) reg probe_upstream_allow;
    (* anyseq *) reg probe_request_valid;
    (* anyseq *) reg [7:0] probe_command_seq;

    // Independent complementary-pair probe over the complete 16-bit space.
    (* anyseq *) reg [7:0] pair_primary;
    (* anyseq *) reg [7:0] pair_inverse;
    wire pair_valid;
    wire pair_fault;

    wire policy_allow;
    wire policy_deny;
    wire execute_pulse;
    wire command_denied;
    wire safe_state;
    wire state_integrity_fault;
    wire authorization_integrity_fault;
    wire authorization_fault_latched;
    wire temporal_integrity_fault;
    wire temporal_fault_latched;
    wire sequence_state_integrity_fault;
    wire fail_closed_active;
    wire [2:0] state_code;
    wire [7:0] expected_command_seq;
    wire [7:0] expected_command_seq_inverse;

    wire ref_allow;
    wire ref_deny;
    wire ref_safe_state;
    wire ref_state_integrity_fault;
    wire ref_authorization_integrity_fault;
    wire ref_authorization_fault_latched;
    wire ref_fail_closed_active;
    wire [2:0] ref_state_code;

    wire probe_execute_pulse;
    wire probe_temporal_integrity_fault;
    wire probe_temporal_fault_latched;
    wire probe_sequence_state_integrity_fault;
    wire [7:0] probe_expected_command_seq;
    wire [7:0] probe_expected_command_seq_inverse;

    localparam [2:0] ST_RESET       = 3'd0;
    localparam [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam [2:0] ST_VERIFY      = 3'd2;
    localparam [2:0] ST_OPERATIONAL = 3'd3;
    localparam [2:0] ST_DEGRADED    = 3'd4;
    localparam [2:0] ST_SAFE        = 3'd5;
    localparam [2:0] ST_RECOVERY    = 3'd6;

    reg past_valid = 1'b0;

    prime_hw_policy_controller_temporal_hardened dut (
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
        .policy_allow(policy_allow),
        .policy_deny(policy_deny),
        .execute_pulse(execute_pulse),
        .command_denied(command_denied),
        .safe_state(safe_state),
        .state_integrity_fault(state_integrity_fault),
        .authorization_integrity_fault(authorization_integrity_fault),
        .authorization_fault_latched(authorization_fault_latched),
        .temporal_integrity_fault(temporal_integrity_fault),
        .temporal_fault_latched(temporal_fault_latched),
        .sequence_state_integrity_fault(sequence_state_integrity_fault),
        .fail_closed_active(fail_closed_active),
        .state_code(state_code),
        .expected_command_seq(expected_command_seq),
        .expected_command_seq_inverse(expected_command_seq_inverse)
    );

    // Exact v0.6 policy reference. Under the declared in-order command protocol,
    // v0.7 must preserve these policy/state outputs while adding execute gating.
    prime_hw_policy_controller_authorization_hardened reference_dut (
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
        .allow(ref_allow),
        .deny(ref_deny),
        .safe_state(ref_safe_state),
        .state_integrity_fault(ref_state_integrity_fault),
        .authorization_integrity_fault(ref_authorization_integrity_fault),
        .authorization_fault_latched(ref_authorization_fault_latched),
        .fail_closed_active(ref_fail_closed_active),
        .state_code(ref_state_code)
    );

    prime_hw_temporal_command_guard probe_guard (
        .clk(clk),
        .reset_n(reset_n),
        .upstream_allow(probe_upstream_allow),
        .request_valid(probe_request_valid),
        .command_seq(probe_command_seq),
        .execute_pulse(probe_execute_pulse),
        .temporal_integrity_fault(probe_temporal_integrity_fault),
        .temporal_fault_latched(probe_temporal_fault_latched),
        .sequence_state_integrity_fault(probe_sequence_state_integrity_fault),
        .expected_command_seq(probe_expected_command_seq),
        .expected_command_seq_inverse(probe_expected_command_seq_inverse)
    );

    prime_hw_sequence_pair_guard pair_probe (
        .expected_seq_primary(pair_primary),
        .expected_seq_inverse(pair_inverse),
        .sequence_state_valid(pair_valid),
        .sequence_state_integrity_fault(pair_fault)
    );

    always @(posedge clk) begin
        past_valid <= 1'b1;

        if (!past_valid)
            assume(!reset_n);
        else
            assume(reset_n);

        // Complete symbolic complementary-pair contract.
        assert(pair_valid == (pair_inverse == ~pair_primary));
        assert(pair_fault == !pair_valid);

        // For the nominal differential path, upstream supplies exactly the
        // current expected command sequence whenever v0.6 grants permission.
        if (past_valid && ref_allow)
            assume(command_seq == expected_command_seq);

        if (past_valid) begin
            // Logical sequence-store integrity is invariant without injection.
            assert(expected_command_seq_inverse == ~expected_command_seq);
            assert(probe_expected_command_seq_inverse == ~probe_expected_command_seq);
            assert(!sequence_state_integrity_fault);
            assert(!probe_sequence_state_integrity_fault);

            // v0.7 preserves v0.6 policy/state behavior for a conforming stream.
            assert(!temporal_integrity_fault);
            assert(!temporal_fault_latched);
            assert(policy_allow == ref_allow);
            assert(policy_deny == ref_deny);
            assert(safe_state == ref_safe_state);
            assert(state_integrity_fault == ref_state_integrity_fault);
            assert(authorization_integrity_fault == ref_authorization_integrity_fault);
            assert(authorization_fault_latched == ref_authorization_fault_latched);
            assert(state_code == ref_state_code);

            // Execution is strictly narrower than policy authorization.
            if (execute_pulse) begin
                assert(policy_allow);
                assert(request_valid);
                assert(command_seq == expected_command_seq);
                assert(!temporal_fault_latched);
                assert(!sequence_state_integrity_fault);
            end

            // Unconstrained probe traffic can execute only the expected command.
            if (probe_execute_pulse) begin
                assert(probe_upstream_allow);
                assert(probe_request_valid);
                assert(probe_command_seq == probe_expected_command_seq);
                assert(!probe_temporal_fault_latched);
                assert(!probe_sequence_state_integrity_fault);
            end
            if (probe_temporal_integrity_fault || probe_temporal_fault_latched || probe_sequence_state_integrity_fault)
                assert(!probe_execute_pulse);

            // Sticky temporal capture and exact successor behavior.
            if ($past(reset_n) && $past(probe_temporal_fault_latched))
                assert(probe_temporal_fault_latched);
            if ($past(reset_n) && $past(probe_temporal_integrity_fault))
                assert(probe_temporal_fault_latched);
            if ($past(reset_n) && $past(probe_execute_pulse))
                assert(probe_expected_command_seq == ($past(probe_expected_command_seq) + 8'd1));
        end

        // Seven inherited semantic states plus six temporal witnesses = 13.
        cover(state_code == ST_RESET);
        cover(state_code == ST_BOOT_LOCKED);
        cover(state_code == ST_VERIFY);
        cover(state_code == ST_OPERATIONAL);
        cover(state_code == ST_DEGRADED);
        cover(state_code == ST_SAFE);
        cover(state_code == ST_RECOVERY);
        cover(execute_pulse);
        cover(probe_execute_pulse);
        cover(probe_temporal_integrity_fault && !probe_sequence_state_integrity_fault);
        cover(probe_temporal_fault_latched);
        cover(pair_fault && !pair_valid);
        cover(pair_valid && !pair_fault);
    end
endmodule
