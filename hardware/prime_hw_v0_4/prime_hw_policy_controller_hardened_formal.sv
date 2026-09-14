`timescale 1ns/1ps

module prime_hw_policy_controller_hardened_formal;
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
    (* anyseq *) reg [7:0] probe_encoded_state;

    wire allow;
    wire deny;
    wire safe_state;
    wire state_integrity_fault;
    wire [2:0] state_code;

    wire probe_valid;
    wire [2:0] probe_semantic_state;

    localparam [2:0] ST_RESET       = 3'd0;
    localparam [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam [2:0] ST_VERIFY      = 3'd2;
    localparam [2:0] ST_OPERATIONAL = 3'd3;
    localparam [2:0] ST_DEGRADED    = 3'd4;
    localparam [2:0] ST_SAFE        = 3'd5;
    localparam [2:0] ST_RECOVERY    = 3'd6;

    localparam [7:0] ST_RESET_CODE       = 8'h00;
    localparam [7:0] ST_BOOT_LOCKED_CODE = 8'h0F;
    localparam [7:0] ST_VERIFY_CODE      = 8'h33;
    localparam [7:0] ST_OPERATIONAL_CODE = 8'h3C;
    localparam [7:0] ST_DEGRADED_CODE    = 8'h55;
    localparam [7:0] ST_SAFE_CODE        = 8'h5A;
    localparam [7:0] ST_RECOVERY_CODE    = 8'h66;

    reg past_valid = 1'b0;
    wire probe_is_valid_code =
        probe_encoded_state == ST_RESET_CODE ||
        probe_encoded_state == ST_BOOT_LOCKED_CODE ||
        probe_encoded_state == ST_VERIFY_CODE ||
        probe_encoded_state == ST_OPERATIONAL_CODE ||
        probe_encoded_state == ST_DEGRADED_CODE ||
        probe_encoded_state == ST_SAFE_CODE ||
        probe_encoded_state == ST_RECOVERY_CODE;

    prime_hw_policy_controller_hardened dut (
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

    prime_hw_state_code_guard probe_guard (
        .encoded_state(probe_encoded_state),
        .state_valid(probe_valid),
        .semantic_state(probe_semantic_state)
    );

    always @(posedge clk) begin
        past_valid <= 1'b1;

        // One reset observation, then released reset for the bounded nominal proof.
        if (!past_valid)
            assume(!reset_n);
        else
            assume(reset_n);

        // The standalone guard is proven across an unconstrained 8-bit probe.
        assert(probe_valid == probe_is_valid_code);
        if (!probe_is_valid_code) begin
            assert(!probe_valid);
            assert(probe_semantic_state == ST_SAFE);
        end

        if (past_valid) begin
            // Nominal transitions from reset must remain inside the valid alphabet.
            assert(!state_integrity_fault);
            assert(state_code <= ST_RECOVERY);
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

        // Seven semantic-state witnesses plus one arbitrary invalid-code witness.
        cover(state_code == ST_RESET);
        cover(state_code == ST_BOOT_LOCKED);
        cover(state_code == ST_VERIFY);
        cover(state_code == ST_OPERATIONAL);
        cover(state_code == ST_DEGRADED);
        cover(state_code == ST_SAFE);
        cover(state_code == ST_RECOVERY);
        cover(!probe_valid);
    end
endmodule
