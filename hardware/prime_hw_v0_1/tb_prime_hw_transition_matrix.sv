`timescale 1ns/1ps

module tb_prime_hw_transition_matrix;
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

    integer vector;
    integer authorization_vector;
    logic [2:0] expected_state;

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

    task automatic clear_controls;
        begin
            boot_verified = 1'b0;
            policy_valid = 1'b0;
            health_degraded = 1'b0;
            fatal_fault = 1'b0;
            recovery_authorized = 1'b0;
            request_valid = 1'b0;
            request_authorized = 1'b0;
            degraded_request_authorized = 1'b0;
        end
    endtask

    task automatic reach_operational;
        begin
            clear_controls();
            reset_n = 1'b0;
            tick();
            reset_n = 1'b1;
            tick();
            expect_state(ST_BOOT_LOCKED, "reach operational: boot locked");
            boot_verified = 1'b1;
            policy_valid = 1'b1;
            tick();
            expect_state(ST_VERIFY, "reach operational: verify");
            tick();
            expect_state(ST_OPERATIONAL, "reach operational: operational");
        end
    endtask

    task automatic reach_degraded;
        begin
            reach_operational();
            health_degraded = 1'b1;
            tick();
            expect_state(ST_DEGRADED, "reach degraded");
        end
    endtask

    task automatic reach_safe;
        begin
            reach_operational();
            fatal_fault = 1'b1;
            tick();
            expect_state(ST_SAFE, "reach safe");
            if (safe_state !== 1'b1 || allow !== 1'b0) begin
                $fatal(1, "reach safe: fail-safe outputs not asserted");
            end
            fatal_fault = 1'b0;
        end
    endtask

    initial begin
        $display("PRIME-HW v0.2 verification boundary: EXHAUSTIVE DECLARED TRANSITION MATRIX + VENDOR-NEUTRAL SYNTHESIS ONLY");

        // Enumerate all combinations of fatal_fault, policy_valid, boot_verified,
        // and health_degraded from OPERATIONAL.
        for (vector = 0; vector < 16; vector = vector + 1) begin
            reach_operational();
            fatal_fault = vector[3];
            policy_valid = vector[2];
            boot_verified = vector[1];
            health_degraded = vector[0];

            if (fatal_fault || !policy_valid || !boot_verified)
                expected_state = ST_SAFE;
            else if (health_degraded)
                expected_state = ST_DEGRADED;
            else
                expected_state = ST_OPERATIONAL;

            tick();
            if (state_code !== expected_state) begin
                $fatal(1,
                    "OP matrix vector %0d failed: fatal=%0b policy=%0b boot=%0b degraded=%0b expected=%0d got=%0d",
                    vector, fatal_fault, policy_valid, boot_verified, health_degraded, expected_state, state_code);
            end
            if ((fatal_fault || !policy_valid || !boot_verified) && allow !== 1'b0) begin
                $fatal(1, "OP matrix vector %0d allowed request under trust/fatal loss", vector);
            end
        end

        // Enumerate the same trust/health combinations from DEGRADED.
        for (vector = 0; vector < 16; vector = vector + 1) begin
            reach_degraded();
            fatal_fault = vector[3];
            policy_valid = vector[2];
            boot_verified = vector[1];
            health_degraded = vector[0];

            if (fatal_fault || !policy_valid || !boot_verified)
                expected_state = ST_SAFE;
            else if (!health_degraded)
                expected_state = ST_OPERATIONAL;
            else
                expected_state = ST_DEGRADED;

            tick();
            if (state_code !== expected_state) begin
                $fatal(1,
                    "DEG matrix vector %0d failed: fatal=%0b policy=%0b boot=%0b degraded=%0b expected=%0d got=%0d",
                    vector, fatal_fault, policy_valid, boot_verified, health_degraded, expected_state, state_code);
            end
        end

        // Enumerate recovery authorization versus fatal fault from SAFE.
        for (vector = 0; vector < 4; vector = vector + 1) begin
            reach_safe();
            recovery_authorized = vector[1];
            fatal_fault = vector[0];
            expected_state = (recovery_authorized && !fatal_fault) ? ST_RECOVERY : ST_SAFE;
            tick();
            if (state_code !== expected_state) begin
                $fatal(1,
                    "SAFE matrix vector %0d failed: recovery=%0b fatal=%0b expected=%0d got=%0d",
                    vector, recovery_authorized, fatal_fault, expected_state, state_code);
            end
        end

        // Exhaust the simple request authorization truth table in OPERATIONAL.
        for (authorization_vector = 0; authorization_vector < 8; authorization_vector = authorization_vector + 1) begin
            reach_operational();
            request_valid = authorization_vector[2];
            request_authorized = authorization_vector[1];
            degraded_request_authorized = authorization_vector[0];
            #1;
            if (allow !== (request_valid && request_authorized)) begin
                $fatal(1, "OP authorization vector %0d produced unexpected allow=%0b", authorization_vector, allow);
            end
            if (deny !== (request_valid && !request_authorized)) begin
                $fatal(1, "OP authorization vector %0d produced unexpected deny=%0b", authorization_vector, deny);
            end
        end

        // Exhaust the request authorization truth table in DEGRADED. Ordinary
        // authorization alone must never substitute for degraded authorization.
        for (authorization_vector = 0; authorization_vector < 8; authorization_vector = authorization_vector + 1) begin
            reach_degraded();
            request_valid = authorization_vector[2];
            request_authorized = authorization_vector[1];
            degraded_request_authorized = authorization_vector[0];
            #1;
            if (allow !== (request_valid && degraded_request_authorized)) begin
                $fatal(1, "DEG authorization vector %0d produced unexpected allow=%0b", authorization_vector, allow);
            end
            if (deny !== (request_valid && !degraded_request_authorized)) begin
                $fatal(1, "DEG authorization vector %0d produced unexpected deny=%0b", authorization_vector, deny);
            end
        end

        $display("PASS: PRIME-HW declared transition/authorization matrix exhausted");
        $finish;
    end
endmodule
