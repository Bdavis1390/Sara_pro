`timescale 1ns/1ps

module tb_prime_hw_policy_controller;
    logic clk = 1'b0;
    logic reset_n = 1'b0;
    logic boot_verified = 1'b0;
    logic policy_valid = 1'b0;
    logic health_degraded = 1'b0;
    logic fatal_fault = 1'b0;
    logic recovery_authorized = 1'b0;
    logic request_valid = 1'b0;
    logic request_authorized = 1'b0;
    logic degraded_request_authorized = 1'b0;
    logic allow;
    logic deny;
    logic safe_state;
    logic [2:0] state_code;

    localparam logic [2:0] ST_RESET       = 3'd0;
    localparam logic [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam logic [2:0] ST_VERIFY      = 3'd2;
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;
    localparam logic [2:0] ST_DEGRADED    = 3'd4;
    localparam logic [2:0] ST_SAFE        = 3'd5;
    localparam logic [2:0] ST_RECOVERY    = 3'd6;

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

    task automatic tick;
        begin
            #5 clk = 1'b1;
            #5 clk = 1'b0;
            #1;
        end
    endtask

    task automatic expect_state(input logic [2:0] expected, input string label_text);
        begin
            if (state_code !== expected) begin
                $fatal(1, "%s: expected state %0d, got %0d", label_text, expected, state_code);
            end
        end
    endtask

    task automatic expect_blocked(input string label_text);
        begin
            if (allow !== 1'b0) begin
                $fatal(1, "%s: protected request unexpectedly allowed", label_text);
            end
        end
    endtask

    initial begin
        $display("PRIME-HW v0.1 claims boundary: RTL REFERENCE / SIMULATION ONLY / NO SILICON OR CERTIFICATION CLAIM");

        request_valid = 1'b1;
        request_authorized = 1'b1;
        tick();
        expect_state(ST_RESET, "reset assertion");
        expect_blocked("reset blocks request");

        reset_n = 1'b1;
        tick();
        expect_state(ST_BOOT_LOCKED, "post-reset boot lock");
        expect_blocked("boot lock blocks request");

        boot_verified = 1'b1;
        policy_valid = 1'b1;
        tick();
        expect_state(ST_VERIFY, "verified boot enters verify");
        expect_blocked("verify blocks request");

        tick();
        expect_state(ST_OPERATIONAL, "valid boot and policy enter operational");
        if (allow !== 1'b1 || deny !== 1'b0) begin
            $fatal(1, "authorized operational request was not allowed");
        end

        request_authorized = 1'b0;
        #1;
        if (allow !== 1'b0 || deny !== 1'b1) begin
            $fatal(1, "unauthorized operational request did not fail closed");
        end

        health_degraded = 1'b1;
        degraded_request_authorized = 1'b1;
        tick();
        expect_state(ST_DEGRADED, "health degradation enters degraded state");
        if (allow !== 1'b1 || deny !== 1'b0) begin
            $fatal(1, "explicitly degraded-authorized request was not allowed in degraded state");
        end

        degraded_request_authorized = 1'b0;
        #1;
        expect_blocked("ordinary request remains blocked in degraded state");

        fatal_fault = 1'b1;
        tick();
        expect_state(ST_SAFE, "fatal fault enters safe state");
        if (safe_state !== 1'b1 || allow !== 1'b0) begin
            $fatal(1, "safe state did not assert fail-safe outputs");
        end

        fatal_fault = 1'b0;
        recovery_authorized = 1'b0;
        tick();
        expect_state(ST_SAFE, "safe state cannot exit without recovery authorization");

        recovery_authorized = 1'b1;
        tick();
        expect_state(ST_RECOVERY, "authorized recovery enters recovery state");
        expect_blocked("recovery blocks protected request");

        recovery_authorized = 1'b0;
        health_degraded = 1'b0;
        tick();
        expect_state(ST_OPERATIONAL, "validated recovery returns operational");

        health_degraded = 1'b1;
        policy_valid = 1'b0;
        tick();
        expect_state(ST_SAFE, "simultaneous trust loss and degradation prioritize safe state");
        if (safe_state !== 1'b1 || allow !== 1'b0) begin
            $fatal(1, "simultaneous trust loss did not assert safe state immediately");
        end

        policy_valid = 1'b1;
        health_degraded = 1'b0;
        recovery_authorized = 1'b1;
        tick();
        expect_state(ST_RECOVERY, "second authorized recovery enters recovery state");
        recovery_authorized = 1'b0;
        tick();
        expect_state(ST_OPERATIONAL, "second recovery returns operational");

        policy_valid = 1'b0;
        tick();
        expect_state(ST_SAFE, "policy loss alone fails safe");
        if (safe_state !== 1'b1) begin
            $fatal(1, "policy-loss safe state not asserted");
        end

        $display("PASS: PRIME-HW v0.1 bounded state/authorization simulation");
        $finish;
    end
endmodule
