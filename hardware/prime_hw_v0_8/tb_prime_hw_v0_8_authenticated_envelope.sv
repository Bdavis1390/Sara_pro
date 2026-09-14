`timescale 1ns/1ps

module tb_prime_hw_v0_8_authenticated_envelope;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg policy_allow;
    reg request_valid;
    reg trusted_epoch_valid;
    reg [31:0] trusted_epoch;
    reg verifier_valid;
    reg [31:0] verified_epoch;
    reg [7:0] verified_seq;
    reg [63:0] verified_command_digest;
    reg [31:0] command_epoch;
    reg [7:0] command_seq;
    reg [63:0] command_digest;
    reg authentication_fault_latched_in;

    wire envelope_binding_valid;
    wire authentication_integrity_fault;
    wire authenticated_allow;

    reg reset_n;
    reg latch_fault_event;
    wire latch_state;

    integer control;
    integer mismatch;
    integer cases;
    reg expected_binding;
    reg expected_fault;
    reg expected_allow;

    prime_hw_authenticated_envelope_guard dut (
        .policy_allow(policy_allow),
        .request_valid(request_valid),
        .trusted_epoch_valid(trusted_epoch_valid),
        .trusted_epoch(trusted_epoch),
        .verifier_valid(verifier_valid),
        .verified_epoch(verified_epoch),
        .verified_seq(verified_seq),
        .verified_command_digest(verified_command_digest),
        .command_epoch(command_epoch),
        .command_seq(command_seq),
        .command_digest(command_digest),
        .authentication_fault_latched(authentication_fault_latched_in),
        .envelope_binding_valid(envelope_binding_valid),
        .authentication_integrity_fault(authentication_integrity_fault),
        .authenticated_allow(authenticated_allow)
    );

    prime_hw_authentication_fault_latch latch_dut (
        .clk(clk),
        .reset_n(reset_n),
        .authentication_integrity_fault(latch_fault_event),
        .authentication_fault_latched(latch_state)
    );

    task fail;
        input [1023:0] message;
        begin
            $display("FAIL: %0s", message);
            $finish(1);
        end
    endtask

    initial begin
        cases = 0;
        reset_n = 1'b0;
        latch_fault_event = 1'b0;

        // Exhaust the abstract control/binding class space: five Boolean control
        // conditions x four independent tuple-mismatch dimensions = 32 * 16.
        for (control = 0; control < 32; control = control + 1) begin
            for (mismatch = 0; mismatch < 16; mismatch = mismatch + 1) begin
                policy_allow = control[0];
                request_valid = control[1];
                trusted_epoch_valid = control[2];
                verifier_valid = control[3];
                authentication_fault_latched_in = control[4];

                trusted_epoch = 32'h1122_3344;
                command_epoch = trusted_epoch ^ (mismatch[0] ? 32'h0000_0001 : 32'h0000_0000);
                verified_epoch = command_epoch ^ (mismatch[1] ? 32'h0000_0001 : 32'h0000_0000);
                command_seq = 8'h5a;
                verified_seq = command_seq ^ (mismatch[2] ? 8'h01 : 8'h00);
                command_digest = 64'h0123_4567_89ab_cdef;
                verified_command_digest = command_digest ^ (mismatch[3] ? 64'h1 : 64'h0);
                #0;

                expected_binding =
                    trusted_epoch_valid && verifier_valid && (mismatch == 0);
                expected_fault =
                    policy_allow && request_valid && !expected_binding;
                expected_allow =
                    policy_allow && request_valid && expected_binding &&
                    !authentication_fault_latched_in;

                if (envelope_binding_valid !== expected_binding)
                    fail("envelope binding predicate mismatch");
                if (authentication_integrity_fault !== expected_fault)
                    fail("authentication fault predicate mismatch");
                if (authenticated_allow !== expected_allow)
                    fail("authenticated allow predicate mismatch");
                if (authenticated_allow && authentication_integrity_fault)
                    fail("authenticated allow and integrity fault asserted together");
                cases = cases + 1;
            end
        end

        if (cases != 512) fail("did not execute all 512 abstract envelope cases");

        // Sticky authentication-fault capture is independent of the combinational
        // guard and persists until reset.
        #2;
        if (latch_state !== 1'b0) fail("authentication latch did not clear on reset");
        @(negedge clk);
        reset_n = 1'b1;
        latch_fault_event = 1'b1;
        @(posedge clk);
        #1;
        if (latch_state !== 1'b1) fail("authentication fault did not latch");
        latch_fault_event = 1'b0;
        repeat (3) begin
            @(posedge clk);
            #1;
            if (latch_state !== 1'b1) fail("authentication fault latch was not sticky");
        end
        reset_n = 1'b0;
        #1;
        if (latch_state !== 1'b0) fail("authentication fault latch did not reset");

        $display("PASS: PRIME-HW v0.8 authenticated-envelope abstract cases=512 field-mismatch dimensions=4 sticky-latch=PASS");
        $finish(0);
    end
endmodule
