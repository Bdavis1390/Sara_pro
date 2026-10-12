`timescale 1ns/1ps

module tb_prime_hw_v0_4_fault_injection;
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

    localparam logic [7:0] ST_RESET_CODE       = 8'h00;
    localparam logic [7:0] ST_BOOT_LOCKED_CODE = 8'h0F;
    localparam logic [7:0] ST_VERIFY_CODE      = 8'h33;
    localparam logic [7:0] ST_OPERATIONAL_CODE = 8'h3C;
    localparam logic [7:0] ST_DEGRADED_CODE    = 8'h55;
    localparam logic [7:0] ST_SAFE_CODE        = 8'h5A;
    localparam logic [7:0] ST_RECOVERY_CODE    = 8'h66;

    integer base_idx;
    integer mask;
    integer injected_cases = 0;
    logic [7:0] corrupted_state;

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

    function automatic integer popcount8(input logic [7:0] value);
        integer i;
        begin
            popcount8 = 0;
            for (i = 0; i < 8; i = i + 1)
                popcount8 = popcount8 + value[i];
        end
    endfunction

    function automatic logic [7:0] code_for_index(input integer idx);
        begin
            case (idx)
                0: code_for_index = ST_RESET_CODE;
                1: code_for_index = ST_BOOT_LOCKED_CODE;
                2: code_for_index = ST_VERIFY_CODE;
                3: code_for_index = ST_OPERATIONAL_CODE;
                4: code_for_index = ST_DEGRADED_CODE;
                5: code_for_index = ST_SAFE_CODE;
                6: code_for_index = ST_RECOVERY_CODE;
                default: code_for_index = 8'hFF;
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

    task automatic expect_state(input logic [2:0] expected, input string label_text);
        begin
            if (state_code !== expected)
                $fatal(1, "%s: expected semantic state %0d, got %0d", label_text, expected, state_code);
            if (state_integrity_fault !== 1'b0)
                $fatal(1, "%s: unexpected state-integrity fault", label_text);
        end
    endtask

    initial begin
        $display("PRIME-HW v0.4 fault-injection regression: RTL verification only / no silicon fault-qualification claim");

        // Generate an explicit asynchronous reset edge.
        #1 reset_n = 1'b0;
        #1;
        expect_state(ST_RESET, "explicit asynchronous reset");
        if (allow !== 1'b0 || deny !== 1'b1)
            $fatal(1, "reset did not fail closed");

        reset_n = 1'b1;
        tick();
        expect_state(ST_BOOT_LOCKED, "boot lock");

        boot_verified = 1'b1;
        policy_valid = 1'b1;
        tick();
        expect_state(ST_VERIFY, "verify");
        tick();
        expect_state(ST_OPERATIONAL, "operational");
        if (allow !== 1'b1 || deny !== 1'b0)
            $fatal(1, "authorized operational request was not allowed");

        // Exhaustively force every corruption at Hamming weight 1, 2, or 3
        // from every valid encoded state. No clock edges occur during a force.
        for (base_idx = 0; base_idx < 7; base_idx = base_idx + 1) begin
            for (mask = 1; mask < 256; mask = mask + 1) begin
                if (popcount8(mask[7:0]) <= 3) begin
                    corrupted_state = code_for_index(base_idx) ^ mask[7:0];
                    force dut.state_q = corrupted_state;
                    #1;
                    injected_cases = injected_cases + 1;

                    if (state_integrity_fault !== 1'b1)
                        $fatal(1, "fault not detected: base=%0d mask=0x%02x corrupted=0x%02x", base_idx, mask[7:0], corrupted_state);
                    if (safe_state !== 1'b1 || state_code !== ST_SAFE)
                        $fatal(1, "fault did not map to semantic SAFE: base=%0d mask=0x%02x", base_idx, mask[7:0]);
                    if (allow !== 1'b0 || deny !== 1'b1)
                        $fatal(1, "fault did not fail closed: base=%0d mask=0x%02x", base_idx, mask[7:0]);

                    release dut.state_q;
                    #1;
                end
            end
        end

        if (injected_cases != 644)
            $fatal(1, "expected 644 <=3-bit fault injections, executed %0d", injected_cases);

        // Do not assume simulator force/release restores the pre-force register
        // value. Re-establish a deterministic architectural state explicitly.
        reset_n = 1'b0;
        #1;
        expect_state(ST_RESET, "post-campaign asynchronous reset");
        reset_n = 1'b1;
        fatal_fault = 1'b0;
        health_degraded = 1'b0;
        recovery_authorized = 1'b0;
        boot_verified = 1'b1;
        policy_valid = 1'b1;
        tick();
        expect_state(ST_BOOT_LOCKED, "post-campaign boot lock");
        tick();
        expect_state(ST_VERIFY, "post-campaign verify");
        tick();
        expect_state(ST_OPERATIONAL, "post-campaign operational");

        // Verify normal fail-safe and recovery semantics remain intact.
        fatal_fault = 1'b1;
        tick();
        expect_state(ST_SAFE, "fatal fault reaches safe");
        if (safe_state !== 1'b1 || allow !== 1'b0)
            $fatal(1, "safe outputs incorrect after fatal fault");

        fatal_fault = 1'b0;
        recovery_authorized = 1'b1;
        tick();
        expect_state(ST_RECOVERY, "authorized recovery");

        recovery_authorized = 1'b0;
        tick();
        expect_state(ST_OPERATIONAL, "recovery returns operational");

        $display("PASS: PRIME-HW v0.4 detected and failed closed for %0d injected <=3-bit encoded-state corruptions", injected_cases);
        $finish;
    end
endmodule
