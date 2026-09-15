`timescale 1ns/1ps

module tb_prime_hw_v0_6_authorization_integrity;
    logic clk = 1'b0;
    logic reset_n = 1'b1;
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
    logic state_integrity_fault;
    logic authorization_integrity_fault;
    logic authorization_fault_latched;
    logic fail_closed_active;
    logic [2:0] state_code;

    logic [2:0] w_state_code;
    logic w_state_integrity_fault;
    logic w_boot_verified;
    logic w_policy_valid;
    logic w_health_degraded;
    logic w_fatal_fault;
    logic w_request_valid;
    logic w_request_authorized;
    logic w_degraded_request_authorized;
    logic w_allow_vote;
    logic w_deny_vote;

    logic v_core_allow;
    logic v_core_deny;
    logic v_witness_allow;
    logic v_witness_deny;
    logic v_request_valid;
    logic v_state_integrity_fault;
    logic v_fault_latched;
    logic v_integrity_fault;
    logic v_allow;
    logic v_deny;

    integer state_i;
    integer bits_i;
    integer voter_i;
    integer witness_cases = 0;
    integer voter_cases = 0;
    logic expected_allow;
    logic expected_deny;
    logic expected_fault;

    localparam logic [2:0] ST_RESET       = 3'd0;
    localparam logic [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam logic [2:0] ST_VERIFY      = 3'd2;
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;
    localparam logic [2:0] ST_DEGRADED    = 3'd4;
    localparam logic [2:0] ST_SAFE        = 3'd5;
    localparam logic [2:0] ST_RECOVERY    = 3'd6;

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

    prime_hw_authorization_witness witness_probe (
        .state_code(w_state_code),
        .state_integrity_fault(w_state_integrity_fault),
        .boot_verified(w_boot_verified),
        .policy_valid(w_policy_valid),
        .health_degraded(w_health_degraded),
        .fatal_fault(w_fatal_fault),
        .request_valid(w_request_valid),
        .request_authorized(w_request_authorized),
        .degraded_request_authorized(w_degraded_request_authorized),
        .allow_vote(w_allow_vote),
        .deny_vote(w_deny_vote)
    );

    prime_hw_authorization_voter voter_probe (
        .core_allow_vote(v_core_allow),
        .core_deny_vote(v_core_deny),
        .witness_allow_vote(v_witness_allow),
        .witness_deny_vote(v_witness_deny),
        .request_valid(v_request_valid),
        .state_integrity_fault(v_state_integrity_fault),
        .authorization_fault_latched(v_fault_latched),
        .authorization_integrity_fault(v_integrity_fault),
        .allow(v_allow),
        .deny(v_deny)
    );

    task automatic tick;
        begin
            #5 clk = 1'b1;
            #1;
            #4 clk = 1'b0;
            #1;
        end
    endtask

    task automatic reset_to_operational;
        begin
            reset_n = 1'b0;
            #1;
            if (state_code !== ST_RESET || authorization_fault_latched !== 1'b0)
                $fatal(1, "reset did not establish clean RESET state");
            reset_n = 1'b1;
            fatal_fault = 1'b0;
            recovery_authorized = 1'b0;
            health_degraded = 1'b0;
            boot_verified = 1'b1;
            policy_valid = 1'b1;
            request_valid = 1'b1;
            request_authorized = 1'b1;
            degraded_request_authorized = 1'b0;
            tick();
            if (state_code !== ST_BOOT_LOCKED) $fatal(1, "expected BOOT_LOCKED");
            tick();
            if (state_code !== ST_VERIFY) $fatal(1, "expected VERIFY");
            tick();
            if (state_code !== ST_OPERATIONAL) $fatal(1, "expected OPERATIONAL");
            if (allow !== 1'b1 || deny !== 1'b0 || authorization_integrity_fault !== 1'b0)
                $fatal(1, "nominal operational authorization mismatch");
        end
    endtask

    task automatic capture_and_escalate_fault(input integer rail_select, input string label_text);
        begin
            // Put both legitimate paths in a deny state, then corrupt exactly one
            // preserved vote rail to create a single-path disagreement.
            request_authorized = 1'b0;
            #1;
            if (allow !== 1'b0 || deny !== 1'b1 || authorization_integrity_fault !== 1'b0)
                $fatal(1, "%s: baseline deny state incorrect", label_text);

            case (rail_select)
                0: force dut.core_allow_vote = 1'b1;
                1: force dut.witness_allow_vote = 1'b1;
                2: force dut.core_deny_vote = 1'b0;
                3: force dut.witness_deny_vote = 1'b0;
                default: $fatal(1, "invalid rail_select");
            endcase
            #1;

            if (authorization_integrity_fault !== 1'b1)
                $fatal(1, "%s: disagreement was not detected", label_text);
            if (allow !== 1'b0 || deny !== 1'b1 || fail_closed_active !== 1'b1)
                $fatal(1, "%s: disagreement did not fail closed immediately", label_text);

            // First edge captures the mismatch into the sticky latch.
            tick();
            if (authorization_fault_latched !== 1'b1)
                $fatal(1, "%s: mismatch was not latched", label_text);

            case (rail_select)
                0: release dut.core_allow_vote;
                1: release dut.witness_allow_vote;
                2: release dut.core_deny_vote;
                3: release dut.witness_deny_vote;
            endcase
            #1;

            if (allow !== 1'b0 || deny !== 1'b1 || authorization_fault_latched !== 1'b1)
                $fatal(1, "%s: sticky fail-close did not persist after fault release", label_text);

            // The latched mismatch is ORed into the core fatal path; the following
            // active edge must converge the underlying semantic controller to SAFE.
            tick();
            if (state_code !== ST_SAFE || safe_state !== 1'b1 || allow !== 1'b0)
                $fatal(1, "%s: sticky authorization fault did not escalate to SAFE", label_text);
        end
    endtask

    initial begin
        $display("PRIME-HW v0.6 authorization-integrity regression: RTL model only / no physical fault-qualification claim");

        // Exhaust the witness truth space: 8 possible 3-bit state values x all
        // 8 Boolean policy/control inputs = 2048 cases.
        for (state_i = 0; state_i < 8; state_i = state_i + 1) begin
            for (bits_i = 0; bits_i < 256; bits_i = bits_i + 1) begin
                w_state_code = state_i[2:0];
                w_state_integrity_fault = bits_i[7];
                w_boot_verified = bits_i[6];
                w_policy_valid = bits_i[5];
                w_health_degraded = bits_i[4];
                w_fatal_fault = bits_i[3];
                w_request_valid = bits_i[2];
                w_request_authorized = bits_i[1];
                w_degraded_request_authorized = bits_i[0];
                #1;

                expected_allow =
                    w_request_valid &&
                    !w_state_integrity_fault &&
                    w_boot_verified && w_policy_valid && !w_fatal_fault &&
                    (((w_state_code == ST_OPERATIONAL) && !w_health_degraded && w_request_authorized) ||
                     ((w_state_code == ST_DEGRADED) && w_degraded_request_authorized));
                expected_deny = w_request_valid && !expected_allow;

                witness_cases = witness_cases + 1;
                if (w_allow_vote !== expected_allow || w_deny_vote !== expected_deny)
                    $fatal(1, "witness truth mismatch state=%0d bits=0x%02x", state_i, bits_i[7:0]);
            end
        end

        if (witness_cases != 2048)
            $fatal(1, "expected 2048 witness cases, executed %0d", witness_cases);

        // Exhaust all 2^7 voter input combinations.
        for (voter_i = 0; voter_i < 128; voter_i = voter_i + 1) begin
            v_core_allow = voter_i[6];
            v_core_deny = voter_i[5];
            v_witness_allow = voter_i[4];
            v_witness_deny = voter_i[3];
            v_request_valid = voter_i[2];
            v_state_integrity_fault = voter_i[1];
            v_fault_latched = voter_i[0];
            #1;

            expected_fault = (v_core_allow != v_witness_allow) || (v_core_deny != v_witness_deny);
            expected_allow =
                v_request_valid && v_core_allow && v_witness_allow &&
                !v_state_integrity_fault && !expected_fault && !v_fault_latched;
            expected_deny = v_request_valid && !expected_allow;

            voter_cases = voter_cases + 1;
            if (v_integrity_fault !== expected_fault || v_allow !== expected_allow || v_deny !== expected_deny)
                $fatal(1, "voter truth mismatch vector=0x%02x", voter_i[6:0]);
        end

        if (voter_cases != 128)
            $fatal(1, "expected 128 voter cases, executed %0d", voter_cases);

        // Four isolated preserved-rail disagreement classes, each from a clean
        // operational baseline. Each must deny immediately, latch, and escalate.
        reset_to_operational();
        capture_and_escalate_fault(0, "core allow stuck-high disagreement");

        reset_to_operational();
        capture_and_escalate_fault(1, "witness allow stuck-high disagreement");

        reset_to_operational();
        capture_and_escalate_fault(2, "core deny stuck-low disagreement");

        reset_to_operational();
        capture_and_escalate_fault(3, "witness deny stuck-low disagreement");

        $display("PASS: PRIME-HW v0.6 witness truth-space=%0d voter truth-space=%0d isolated rail faults=4",
                 witness_cases, voter_cases);
        $finish;
    end
endmodule
