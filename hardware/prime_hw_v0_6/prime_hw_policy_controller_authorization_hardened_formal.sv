`timescale 1ns/1ps

module prime_hw_policy_controller_authorization_hardened_formal;
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

    // Standalone witness probe.
    (* anyseq *) reg [2:0] probe_state_code;
    (* anyseq *) reg probe_state_fault;
    (* anyseq *) reg probe_boot;
    (* anyseq *) reg probe_policy;
    (* anyseq *) reg probe_health;
    (* anyseq *) reg probe_fatal;
    (* anyseq *) reg probe_request_valid;
    (* anyseq *) reg probe_request_authorized;
    (* anyseq *) reg probe_degraded_authorized;
    wire probe_witness_allow;
    wire probe_witness_deny;

    // Standalone voter probe.
    (* anyseq *) reg probe_core_allow;
    (* anyseq *) reg probe_core_deny;
    (* anyseq *) reg probe_vote_allow;
    (* anyseq *) reg probe_vote_deny;
    (* anyseq *) reg probe_vote_request_valid;
    (* anyseq *) reg probe_vote_state_fault;
    (* anyseq *) reg probe_vote_latched;
    wire probe_vote_integrity_fault;
    wire probe_final_allow;
    wire probe_final_deny;

    // Standalone sticky-latch probe.
    (* anyseq *) reg probe_fault_event;
    wire probe_fault_latched;

    wire allow;
    wire deny;
    wire safe_state;
    wire state_integrity_fault;
    wire authorization_integrity_fault;
    wire authorization_fault_latched;
    wire fail_closed_active;
    wire [2:0] state_code;

    wire ref_allow;
    wire ref_deny;
    wire ref_safe_state;
    wire ref_state_integrity_fault;
    wire [2:0] ref_state_code;

    localparam [2:0] ST_RESET       = 3'd0;
    localparam [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam [2:0] ST_VERIFY      = 3'd2;
    localparam [2:0] ST_OPERATIONAL = 3'd3;
    localparam [2:0] ST_DEGRADED    = 3'd4;
    localparam [2:0] ST_SAFE        = 3'd5;
    localparam [2:0] ST_RECOVERY    = 3'd6;

    reg past_valid = 1'b0;

    wire expected_witness_allow =
        probe_request_valid &&
        !probe_state_fault &&
        probe_boot && probe_policy && !probe_fatal &&
        (((probe_state_code == ST_OPERATIONAL) && !probe_health && probe_request_authorized) ||
         ((probe_state_code == ST_DEGRADED) && probe_degraded_authorized));
    wire expected_witness_deny = probe_request_valid && !expected_witness_allow;

    wire expected_vote_fault =
        (probe_core_allow != probe_vote_allow) ||
        (probe_core_deny != probe_vote_deny);
    wire expected_final_allow =
        probe_vote_request_valid &&
        probe_core_allow && probe_vote_allow &&
        !probe_vote_state_fault &&
        !expected_vote_fault &&
        !probe_vote_latched;
    wire expected_final_deny = probe_vote_request_valid && !expected_final_allow;

    prime_hw_policy_controller_authorization_hardened dut (
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
        .allow(allow),
        .deny(deny),
        .safe_state(safe_state),
        .state_integrity_fault(state_integrity_fault),
        .authorization_integrity_fault(authorization_integrity_fault),
        .authorization_fault_latched(authorization_fault_latched),
        .fail_closed_active(fail_closed_active),
        .state_code(state_code)
    );

    // Nominal reference is the exact v0.5 controller beneath this increment.
    prime_hw_policy_controller_diverse reference_dut (
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
        .state_code(ref_state_code)
    );

    prime_hw_authorization_witness witness_probe (
        .state_code(probe_state_code),
        .state_integrity_fault(probe_state_fault),
        .boot_verified(probe_boot),
        .policy_valid(probe_policy),
        .health_degraded(probe_health),
        .fatal_fault(probe_fatal),
        .request_valid(probe_request_valid),
        .request_authorized(probe_request_authorized),
        .degraded_request_authorized(probe_degraded_authorized),
        .allow_vote(probe_witness_allow),
        .deny_vote(probe_witness_deny)
    );

    prime_hw_authorization_voter voter_probe (
        .core_allow_vote(probe_core_allow),
        .core_deny_vote(probe_core_deny),
        .witness_allow_vote(probe_vote_allow),
        .witness_deny_vote(probe_vote_deny),
        .request_valid(probe_vote_request_valid),
        .state_integrity_fault(probe_vote_state_fault),
        .authorization_fault_latched(probe_vote_latched),
        .authorization_integrity_fault(probe_vote_integrity_fault),
        .allow(probe_final_allow),
        .deny(probe_final_deny)
    );

    prime_hw_authorization_fault_latch latch_probe (
        .clk(clk),
        .reset_n(reset_n),
        .authorization_integrity_fault(probe_fault_event),
        .authorization_fault_latched(probe_fault_latched)
    );

    always @(posedge clk) begin
        past_valid <= 1'b1;

        if (!past_valid)
            assume(!reset_n);
        else
            assume(reset_n);

        // Complete combinational truth contracts for the independent witness
        // and fail-closed voter over unconstrained symbolic inputs.
        assert(probe_witness_allow == expected_witness_allow);
        assert(probe_witness_deny == expected_witness_deny);
        assert(probe_vote_integrity_fault == expected_vote_fault);
        assert(probe_final_allow == expected_final_allow);
        assert(probe_final_deny == expected_final_deny);

        // Disagreement or either upstream integrity state cannot produce allow.
        if (expected_vote_fault || probe_vote_state_fault || probe_vote_latched)
            assert(!probe_final_allow);
        if (probe_final_allow) begin
            assert(probe_core_allow);
            assert(probe_vote_allow);
            assert(probe_vote_request_valid);
            assert(!expected_vote_fault);
        end

        if (past_valid) begin
            // Standalone authorization-fault latch is sticky while reset remains released.
            if ($past(reset_n) && $past(probe_fault_latched))
                assert(probe_fault_latched);
            if ($past(reset_n) && $past(probe_fault_event))
                assert(probe_fault_latched);

            // On the nominal unmutated controller path, the independent witness
            // and core authorization paths must agree continuously.
            assert(!authorization_integrity_fault);
            assert(!authorization_fault_latched);
            assert(state_integrity_fault == ref_state_integrity_fault);
            assert(state_code == ref_state_code);
            assert(allow == ref_allow);
            assert(deny == ref_deny);
            assert(safe_state == ref_safe_state);

            assert(!(allow && deny));
            if (allow) begin
                assert(request_valid);
                assert(!state_integrity_fault);
                assert(!authorization_integrity_fault);
                assert(!authorization_fault_latched);
            end
        end

        // Nominal semantic states plus authorization/witness fault classes.
        cover(state_code == ST_RESET);
        cover(state_code == ST_BOOT_LOCKED);
        cover(state_code == ST_VERIFY);
        cover(state_code == ST_OPERATIONAL);
        cover(state_code == ST_DEGRADED);
        cover(state_code == ST_SAFE);
        cover(state_code == ST_RECOVERY);
        cover(probe_witness_allow && probe_state_code == ST_OPERATIONAL);
        cover(probe_witness_allow && probe_state_code == ST_DEGRADED);
        cover(expected_vote_fault);
        cover(probe_vote_state_fault && !expected_vote_fault);
        cover(probe_fault_latched);
    end
endmodule
