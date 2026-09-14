`timescale 1ns/1ps

module prime_hw_policy_controller_diverse_formal;
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

    (* anyseq *) reg [7:0] probe_primary;
    (* anyseq *) reg [6:0] probe_shadow;

    wire allow;
    wire deny;
    wire safe_state;
    wire state_integrity_fault;
    wire [2:0] state_code;

    wire ref_allow;
    wire ref_deny;
    wire ref_safe_state;
    wire [2:0] ref_state_code;

    wire probe_primary_valid;
    wire probe_shadow_valid;
    wire probe_fault;
    wire [2:0] probe_semantic;

    localparam [2:0] ST_RESET       = 3'd0;
    localparam [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam [2:0] ST_VERIFY      = 3'd2;
    localparam [2:0] ST_OPERATIONAL = 3'd3;
    localparam [2:0] ST_DEGRADED    = 3'd4;
    localparam [2:0] ST_SAFE        = 3'd5;
    localparam [2:0] ST_RECOVERY    = 3'd6;

    reg past_valid = 1'b0;

    wire probe_pair_exact =
        ((probe_primary == 8'h00) && (probe_shadow == 7'b0000001)) ||
        ((probe_primary == 8'h0F) && (probe_shadow == 7'b0000010)) ||
        ((probe_primary == 8'h33) && (probe_shadow == 7'b0000100)) ||
        ((probe_primary == 8'h3C) && (probe_shadow == 7'b0001000)) ||
        ((probe_primary == 8'h55) && (probe_shadow == 7'b0010000)) ||
        ((probe_primary == 8'h5A) && (probe_shadow == 7'b0100000)) ||
        ((probe_primary == 8'h66) && (probe_shadow == 7'b1000000));

    prime_hw_policy_controller_diverse dut (
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
        .state_code(state_code)
    );

    // Nominal semantic oracle remains the inherited v0.1 controller.
    prime_hw_policy_controller reference_dut (
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
        .state_code(ref_state_code)
    );

    // Independent unconstrained 15-bit probe proves the complete combinational
    // acceptance set of the dual-representation guard, not merely sampled masks.
    prime_hw_dual_state_guard probe_guard (
        .primary_state(probe_primary),
        .shadow_state(probe_shadow),
        .primary_valid(probe_primary_valid),
        .shadow_valid(probe_shadow_valid),
        .state_integrity_fault(probe_fault),
        .semantic_state(probe_semantic)
    );

    always @(posedge clk) begin
        past_valid <= 1'b1;

        if (!past_valid)
            assume(!reset_n);
        else
            assume(reset_n);

        // Complete 2^15-pair guard contract.
        assert(probe_fault == !probe_pair_exact);
        if (probe_fault)
            assert(probe_semantic == ST_SAFE);

        if (past_valid) begin
            // No integrity fault is permitted on the nominal synchronized path.
            assert(!state_integrity_fault);
            assert(state_code == ref_state_code);
            assert(allow == ref_allow);
            assert(deny == ref_deny);
            assert(safe_state == ref_safe_state);
            assert(!(allow && deny));
            assert(safe_state == (state_code == ST_SAFE));

            if (state_code != ST_OPERATIONAL && state_code != ST_DEGRADED)
                assert(!allow);

            if (($past(state_code) == ST_OPERATIONAL || $past(state_code) == ST_DEGRADED) &&
                ($past(fatal_fault) || !$past(policy_valid) || !$past(boot_verified)))
                assert(state_code == ST_SAFE);

            if ($past(state_code) == ST_OPERATIONAL &&
                !$past(fatal_fault) && $past(policy_valid) && $past(boot_verified) &&
                $past(health_degraded))
                assert(state_code == ST_DEGRADED);

            if ($past(state_code) == ST_DEGRADED &&
                !$past(fatal_fault) && $past(policy_valid) && $past(boot_verified) &&
                !$past(health_degraded))
                assert(state_code == ST_OPERATIONAL);

            if ($past(state_code) == ST_SAFE &&
                (!$past(recovery_authorized) || $past(fatal_fault)))
                assert(state_code == ST_SAFE);

            if ($past(state_code) == ST_SAFE &&
                $past(recovery_authorized) && !$past(fatal_fault))
                assert(state_code == ST_RECOVERY);
        end

        // Nominal-state reachability plus the three distinct guard-fault classes.
        cover(state_code == ST_RESET);
        cover(state_code == ST_BOOT_LOCKED);
        cover(state_code == ST_VERIFY);
        cover(state_code == ST_OPERATIONAL);
        cover(state_code == ST_DEGRADED);
        cover(state_code == ST_SAFE);
        cover(state_code == ST_RECOVERY);
        cover(!probe_primary_valid);
        cover(!probe_shadow_valid);
        cover(probe_primary_valid && probe_shadow_valid && probe_fault);
    end
endmodule
