`timescale 1ns/1ps

module tb_prime_hw_v0_5_dual_state_faults;
    logic clk = 1'b0;
    logic reset_n = 1'b1;
    logic boot_verified = 1'b0;
    logic policy_valid = 1'b0;
    logic health_degraded = 1'b0;
    logic fatal_fault = 1'b0;
    logic recovery_authorized = 1'b0;
    logic request_valid = 1'b1;
    logic request_authorized = 1'b1;
    logic degraded_request_authorized = 1'b1;

    logic allow;
    logic deny;
    logic safe_state;
    logic state_integrity_fault;
    logic [2:0] state_code;

    localparam logic [2:0] ST_RESET       = 3'd0;
    localparam logic [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam logic [2:0] ST_VERIFY      = 3'd2;
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;
    localparam logic [2:0] ST_DEGRADED    = 3'd4;
    localparam logic [2:0] ST_SAFE        = 3'd5;
    localparam logic [2:0] ST_RECOVERY    = 3'd6;

    integer base_idx;
    integer mask;
    integer primary_cases = 0;
    integer shadow_cases = 0;
    logic [7:0] corrupted_primary;
    logic [6:0] corrupted_shadow;

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

    function automatic logic [7:0] primary_code(input integer idx);
        begin
            case (idx)
                0: primary_code = 8'h00;
                1: primary_code = 8'h0F;
                2: primary_code = 8'h33;
                3: primary_code = 8'h3C;
                4: primary_code = 8'h55;
                5: primary_code = 8'h5A;
                6: primary_code = 8'h66;
                default: primary_code = 8'hFF;
            endcase
        end
    endfunction

    function automatic logic [6:0] shadow_code(input integer idx);
        begin
            case (idx)
                0: shadow_code = 7'b0000001;
                1: shadow_code = 7'b0000010;
                2: shadow_code = 7'b0000100;
                3: shadow_code = 7'b0001000;
                4: shadow_code = 7'b0010000;
                5: shadow_code = 7'b0100000;
                6: shadow_code = 7'b1000000;
                default: shadow_code = 7'b1111111;
            endcase
        end
    endfunction

    task automatic tick;
        begin
            #5 clk = 1'b1;
            #1;
            #4 clk = 1'b0;
            #1;
        end
    endtask

    task automatic expect_nominal_state(input logic [2:0] expected, input string label_text);
        begin
            if (state_integrity_fault !== 1'b0)
                $fatal(1, "%s: unexpected state-integrity fault", label_text);
            if (state_code !== expected)
                $fatal(1, "%s: expected semantic state %0d, got %0d", label_text, expected, state_code);
        end
    endtask

    task automatic expect_fault_closed(input string label_text);
        begin
            if (state_integrity_fault !== 1'b1)
                $fatal(1, "%s: state-integrity fault was not asserted", label_text);
            if (state_code !== ST_SAFE || safe_state !== 1'b1)
                $fatal(1, "%s: integrity fault did not report semantic SAFE", label_text);
            if (allow !== 1'b0 || deny !== 1'b1)
                $fatal(1, "%s: integrity fault did not fail closed", label_text);
        end
    endtask

    initial begin
        $display("PRIME-HW v0.5 dual-state mutation regression: RTL model only / no physical fault-qualification claim");

        // Explicit asynchronous reset, then nominal path to OPERATIONAL.
        #1 reset_n = 1'b0;
        #1;
        expect_nominal_state(ST_RESET, "reset");
        reset_n = 1'b1;
        tick();
        expect_nominal_state(ST_BOOT_LOCKED, "boot locked");
        boot_verified = 1'b1;
        policy_valid = 1'b1;
        tick();
        expect_nominal_state(ST_VERIFY, "verify");
        tick();
        expect_nominal_state(ST_OPERATIONAL, "operational");
        if (allow !== 1'b1 || deny !== 1'b0)
            $fatal(1, "nominal authorized request was not allowed");

        // Campaign A: arbitrary nonzero corruption in the 8-bit primary state
        // while the one-hot shadow remains at the matching uncorrupted state.
        // This includes corruptions that alias another valid primary codeword.
        for (base_idx = 0; base_idx < 7; base_idx = base_idx + 1) begin
            for (mask = 1; mask < 256; mask = mask + 1) begin
                corrupted_primary = primary_code(base_idx) ^ mask[7:0];
                force dut.primary_state_q = corrupted_primary;
                force dut.shadow_state_q = shadow_code(base_idx);
                #1;
                primary_cases = primary_cases + 1;
                expect_fault_closed("primary-domain mutation");
                release dut.primary_state_q;
                release dut.shadow_state_q;
                #1;
            end
        end

        // Campaign B: arbitrary nonzero corruption in the 7-bit one-hot shadow
        // while the distance-coded primary remains at the matching state.
        // This includes two-bit one-hot-to-one-hot alias transitions.
        for (base_idx = 0; base_idx < 7; base_idx = base_idx + 1) begin
            for (mask = 1; mask < 128; mask = mask + 1) begin
                corrupted_shadow = shadow_code(base_idx) ^ mask[6:0];
                force dut.primary_state_q = primary_code(base_idx);
                force dut.shadow_state_q = corrupted_shadow;
                #1;
                shadow_cases = shadow_cases + 1;
                expect_fault_closed("shadow-domain mutation");
                release dut.primary_state_q;
                release dut.shadow_state_q;
                #1;
            end
        end

        if (primary_cases != 1785)
            $fatal(1, "expected 1785 primary-domain mutations, executed %0d", primary_cases);
        if (shadow_cases != 889)
            $fatal(1, "expected 889 shadow-domain mutations, executed %0d", shadow_cases);

        // Re-establish deterministic architectural state after force/release.
        reset_n = 1'b0;
        #1;
        expect_nominal_state(ST_RESET, "post-campaign reset");
        reset_n = 1'b1;
        fatal_fault = 1'b0;
        health_degraded = 1'b0;
        recovery_authorized = 1'b0;
        boot_verified = 1'b1;
        policy_valid = 1'b1;
        tick();
        expect_nominal_state(ST_BOOT_LOCKED, "post-campaign boot lock");
        tick();
        expect_nominal_state(ST_VERIFY, "post-campaign verify");
        tick();
        expect_nominal_state(ST_OPERATIONAL, "post-campaign operational");

        // Preserve nominal fail-safe and recovery semantics.
        health_degraded = 1'b1;
        tick();
        expect_nominal_state(ST_DEGRADED, "degraded");
        fatal_fault = 1'b1;
        tick();
        expect_nominal_state(ST_SAFE, "fatal fault safe");
        fatal_fault = 1'b0;
        recovery_authorized = 1'b1;
        tick();
        expect_nominal_state(ST_RECOVERY, "authorized recovery");
        recovery_authorized = 1'b0;
        health_degraded = 1'b0;
        tick();
        expect_nominal_state(ST_OPERATIONAL, "recovered operational");

        $display("PASS: PRIME-HW v0.5 failed closed for %0d primary + %0d shadow = %0d isolated arbitrary state-domain mutations",
                 primary_cases, shadow_cases, primary_cases + shadow_cases);
        $finish;
    end
endmodule
