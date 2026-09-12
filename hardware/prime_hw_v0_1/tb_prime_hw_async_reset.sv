`timescale 1ns/1ps

module tb_prime_hw_async_reset;
    logic clk = 1'b0;
    logic reset_n = 1'b0;
    logic boot_verified = 1'b0;
    logic policy_valid = 1'b0;
    logic health_degraded = 1'b0;
    logic fatal_fault = 1'b0;
    logic recovery_authorized = 1'b0;
    logic request_valid = 1'b1;
    logic request_authorized = 1'b1;
    logic degraded_request_authorized = 1'b0;
    logic allow;
    logic deny;
    logic safe_state;
    logic [2:0] state_code;

    localparam logic [2:0] ST_RESET       = 3'd0;
    localparam logic [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam logic [2:0] ST_VERIFY      = 3'd2;
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;

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

    always #5 clk = ~clk;

    task automatic expect_state(input logic [2:0] expected, input string label_text);
        if (state_code !== expected)
            $fatal(1, "%s: expected state %0d, got %0d", label_text, expected, state_code);
    endtask

    task automatic expect_blocked(input string label_text);
        if (allow !== 1'b0)
            $fatal(1, "%s: protected request unexpectedly allowed", label_text);
    endtask

    initial begin
        $display("PRIME-HW async-reset regression: native RTL only / no formal-equivalence claim");

        // Initial asynchronous reset establishes RESET.
        #1;
        expect_state(ST_RESET, "initial reset");
        expect_blocked("initial reset blocks request");

        // Release reset and advance to OPERATIONAL on normal clock edges.
        reset_n = 1'b1;
        @(posedge clk); #1;
        expect_state(ST_BOOT_LOCKED, "release reaches boot lock");

        boot_verified = 1'b1;
        policy_valid = 1'b1;
        @(posedge clk); #1;
        expect_state(ST_VERIFY, "verified boot reaches verify");
        @(posedge clk); #1;
        expect_state(ST_OPERATIONAL, "trusted system reaches operational");
        if (allow !== 1'b1 || deny !== 1'b0)
            $fatal(1, "authorized request was not allowed before reset pulse");

        // Assert reset strictly between active clock edges. State must reset without
        // waiting for a posedge because the native RTL sensitivity includes negedge reset_n.
        @(negedge clk); #2;
        reset_n = 1'b0;
        #1;
        expect_state(ST_RESET, "mid-cycle asynchronous reset assertion");
        expect_blocked("mid-cycle reset immediately blocks request");

        // Releasing reset between edges must not advance state until the next posedge.
        #1;
        reset_n = 1'b1;
        #1;
        expect_state(ST_RESET, "mid-cycle reset release holds reset state until clock");
        expect_blocked("released reset remains blocked before next clock");

        @(posedge clk); #1;
        expect_state(ST_BOOT_LOCKED, "first clock after reset release reaches boot lock");
        expect_blocked("post-reset boot lock blocks request");

        $display("PASS: PRIME-HW native asynchronous-reset pulse regression");
        $finish;
    end
endmodule
