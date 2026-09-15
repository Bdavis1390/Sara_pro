`timescale 1ns/1ps

module prime_hw_policy_controller_formal;
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

    wire allow;
    wire deny;
    wire safe_state;
    wire [2:0] state_code;

    localparam [2:0] ST_RESET       = 3'd0;
    localparam [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam [2:0] ST_VERIFY      = 3'd2;
    localparam [2:0] ST_OPERATIONAL = 3'd3;
    localparam [2:0] ST_DEGRADED    = 3'd4;
    localparam [2:0] ST_SAFE        = 3'd5;
    localparam [2:0] ST_RECOVERY    = 3'd6;

    reg past_valid = 1'b0;

    prime_hw_policy_controller dut (
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
        .state_code(state_code)
    );

    always @(posedge clk) begin
        past_valid <= 1'b1;

        // Establish one reset edge, then hold reset released for the bounded proof.
        if (!past_valid)
            assume(!reset_n);
        else
            assume(reset_n);

        if (past_valid) begin
            // Output-safety invariants.
            assert(!(allow && deny));
            assert(safe_state == (state_code == ST_SAFE));

            if (state_code != ST_OPERATIONAL && state_code != ST_DEGRADED)
                assert(!allow);

            if (allow && state_code == ST_OPERATIONAL) begin
                assert(request_valid);
                assert(request_authorized);
                assert(boot_verified);
                assert(policy_valid);
                assert(!fatal_fault);
                assert(!health_degraded);
            end

            if (allow && state_code == ST_DEGRADED) begin
                assert(request_valid);
                assert(degraded_request_authorized);
                assert(boot_verified);
                assert(policy_valid);
                assert(!fatal_fault);
            end

            // Trust/fatal loss from an active state must fail SAFE on the next state.
            if (($past(state_code) == ST_OPERATIONAL || $past(state_code) == ST_DEGRADED) &&
                ($past(fatal_fault) || !$past(policy_valid) || !$past(boot_verified))) begin
                assert(state_code == ST_SAFE);
            end

            // Health degradation alone from OPERATIONAL must enter DEGRADED.
            if ($past(state_code) == ST_OPERATIONAL &&
                !$past(fatal_fault) && $past(policy_valid) && $past(boot_verified) &&
                $past(health_degraded)) begin
                assert(state_code == ST_DEGRADED);
            end

            // Healthy trusted DEGRADED state must return to OPERATIONAL.
            if ($past(state_code) == ST_DEGRADED &&
                !$past(fatal_fault) && $past(policy_valid) && $past(boot_verified) &&
                !$past(health_degraded)) begin
                assert(state_code == ST_OPERATIONAL);
            end

            // SAFE is sticky unless explicitly authorized to recover and no fatal fault exists.
            if ($past(state_code) == ST_SAFE &&
                (!$past(recovery_authorized) || $past(fatal_fault))) begin
                assert(state_code == ST_SAFE);
            end

            if ($past(state_code) == ST_SAFE &&
                $past(recovery_authorized) && !$past(fatal_fault)) begin
                assert(state_code == ST_RECOVERY);
            end
        end

        // Principal-state reachability witnesses.
        cover(state_code == ST_OPERATIONAL);
        cover(state_code == ST_DEGRADED);
        cover(state_code == ST_SAFE);
        cover(state_code == ST_RECOVERY);

        // Assertion-family witnesses: demonstrate that the bounded environment can
        // actually exercise the guarded safety properties rather than proving them
        // only because their antecedents are unreachable.
        cover(past_valid && state_code == ST_OPERATIONAL && allow);
        cover(past_valid && state_code == ST_DEGRADED && allow);

        cover(past_valid &&
              ($past(state_code) == ST_OPERATIONAL || $past(state_code) == ST_DEGRADED) &&
              ($past(fatal_fault) || !$past(policy_valid) || !$past(boot_verified)) &&
              state_code == ST_SAFE);

        cover(past_valid &&
              $past(state_code) == ST_OPERATIONAL &&
              !$past(fatal_fault) && $past(policy_valid) && $past(boot_verified) &&
              $past(health_degraded) && state_code == ST_DEGRADED);

        cover(past_valid &&
              $past(state_code) == ST_DEGRADED &&
              !$past(fatal_fault) && $past(policy_valid) && $past(boot_verified) &&
              !$past(health_degraded) && state_code == ST_OPERATIONAL);

        cover(past_valid &&
              $past(state_code) == ST_SAFE &&
              !$past(recovery_authorized) && state_code == ST_SAFE);

        cover(past_valid &&
              $past(state_code) == ST_SAFE &&
              $past(recovery_authorized) && $past(fatal_fault) &&
              state_code == ST_SAFE);

        cover(past_valid &&
              $past(state_code) == ST_SAFE &&
              $past(recovery_authorized) && !$past(fatal_fault) &&
              state_code == ST_RECOVERY);
    end
endmodule
