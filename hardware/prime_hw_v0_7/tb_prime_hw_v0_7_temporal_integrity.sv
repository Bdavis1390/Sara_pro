`timescale 1ns/1ps

module tb_prime_hw_v0_7_temporal_integrity;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg reset_n;
    reg upstream_allow;
    reg request_valid;
    reg [7:0] command_seq;

    wire execute_pulse;
    wire temporal_integrity_fault;
    wire temporal_fault_latched;
    wire sequence_state_integrity_fault;
    wire [7:0] expected_command_seq;
    wire [7:0] expected_command_seq_inverse;

    reg [7:0] probe_primary;
    reg [7:0] probe_inverse;
    wire probe_valid;
    wire probe_fault;

    integer i;
    integer j;
    integer valid_pairs;
    integer invalid_pairs;

    prime_hw_sequence_pair_guard probe_guard (
        .expected_seq_primary(probe_primary),
        .expected_seq_inverse(probe_inverse),
        .sequence_state_valid(probe_valid),
        .sequence_state_integrity_fault(probe_fault)
    );

    prime_hw_temporal_command_guard dut (
        .clk(clk),
        .reset_n(reset_n),
        .upstream_allow(upstream_allow),
        .request_valid(request_valid),
        .command_seq(command_seq),
        .execute_pulse(execute_pulse),
        .temporal_integrity_fault(temporal_integrity_fault),
        .temporal_fault_latched(temporal_fault_latched),
        .sequence_state_integrity_fault(sequence_state_integrity_fault),
        .expected_command_seq(expected_command_seq),
        .expected_command_seq_inverse(expected_command_seq_inverse)
    );

    task fail;
        input [1023:0] message;
        begin
            $display("FAIL: %0s", message);
            $finish(1);
        end
    endtask

    task reset_guard;
        begin
            reset_n = 1'b0;
            upstream_allow = 1'b0;
            request_valid = 1'b0;
            command_seq = 8'h00;
            #2;
            if (expected_command_seq !== 8'h00) fail("reset primary sequence is not zero");
            if (expected_command_seq_inverse !== 8'hff) fail("reset inverse sequence is not ff");
            if (temporal_fault_latched !== 1'b0) fail("temporal fault latch did not clear on reset");
            if (sequence_state_integrity_fault !== 1'b0) fail("sequence state invalid during reset baseline");
            @(negedge clk);
            reset_n = 1'b1;
            #1;
        end
    endtask

    task issue_valid;
        input [7:0] seq;
        begin
            @(negedge clk);
            upstream_allow = 1'b1;
            request_valid = 1'b1;
            command_seq = seq;
            #1;
            if (expected_command_seq !== seq) fail("valid command does not match expected sequence");
            if (execute_pulse !== 1'b1) fail("valid in-order approved command did not execute");
            if (temporal_integrity_fault !== 1'b0) fail("valid in-order command asserted temporal fault before acceptance");
            @(posedge clk);
            #1;
            upstream_allow = 1'b0;
            request_valid = 1'b0;
            command_seq = 8'h00;
            #1;
            if (temporal_fault_latched !== 1'b0) fail("valid command latched temporal fault");
        end
    endtask

    initial begin
        reset_n = 1'b0;
        upstream_allow = 1'b0;
        request_valid = 1'b0;
        command_seq = 8'h00;
        probe_primary = 8'h00;
        probe_inverse = 8'hff;
        valid_pairs = 0;
        invalid_pairs = 0;

        // Exhaust the complete 8+8-bit complementary sequence-state space.
        for (i = 0; i < 256; i = i + 1) begin
            for (j = 0; j < 256; j = j + 1) begin
                probe_primary = i[7:0];
                probe_inverse = j[7:0];
                #0;
                if (j[7:0] == ~i[7:0]) begin
                    valid_pairs = valid_pairs + 1;
                    if (probe_valid !== 1'b1 || probe_fault !== 1'b0)
                        fail("complementary sequence pair rejected");
                end else begin
                    invalid_pairs = invalid_pairs + 1;
                    if (probe_valid !== 1'b0 || probe_fault !== 1'b1)
                        fail("non-complementary sequence pair accepted");
                end
            end
        end
        if (valid_pairs != 256) fail("valid sequence-pair count is not 256");
        if (invalid_pairs != 65280) fail("invalid sequence-pair count is not 65280");

        // Nominal exactly-once progression.
        reset_guard();
        issue_valid(8'h00);
        if (expected_command_seq !== 8'h01) fail("sequence did not advance after command zero");
        issue_valid(8'h01);
        if (expected_command_seq !== 8'h02) fail("sequence did not advance after command one");

        // Unauthorized traffic neither executes nor poisons sequence state.
        reset_guard();
        @(negedge clk);
        upstream_allow = 1'b0;
        request_valid = 1'b1;
        command_seq = 8'hc8;
        #1;
        if (execute_pulse !== 1'b0) fail("unauthorized command executed");
        if (temporal_integrity_fault !== 1'b0) fail("unauthorized mismatch poisoned temporal state");
        @(posedge clk);
        #1;
        if (expected_command_seq !== 8'h00 || temporal_fault_latched !== 1'b0)
            fail("unauthorized mismatch changed temporal state");

        // Future/out-of-order approved command fails closed and latches.
        reset_guard();
        @(negedge clk);
        upstream_allow = 1'b1;
        request_valid = 1'b1;
        command_seq = 8'h07;
        #1;
        if (execute_pulse !== 1'b0 || temporal_integrity_fault !== 1'b1)
            fail("future command did not fail closed immediately");
        @(posedge clk);
        #1;
        if (temporal_fault_latched !== 1'b1) fail("future command fault did not latch");
        if (execute_pulse !== 1'b0) fail("latched temporal fault allowed execution");

        // Stale replay after two accepted transactions fails closed.
        reset_guard();
        issue_valid(8'h00);
        issue_valid(8'h01);
        @(negedge clk);
        upstream_allow = 1'b1;
        request_valid = 1'b1;
        command_seq = 8'h00;
        #1;
        if (execute_pulse !== 1'b0 || temporal_integrity_fault !== 1'b1)
            fail("stale replay did not fail closed");
        @(posedge clk);
        #1;
        if (temporal_fault_latched !== 1'b1) fail("stale replay did not latch fault");

        // A held request can execute once only; remaining asserted into the next
        // sampling edge is treated as a duplicate transaction and latched.
        reset_guard();
        @(negedge clk);
        upstream_allow = 1'b1;
        request_valid = 1'b1;
        command_seq = 8'h00;
        #1;
        if (execute_pulse !== 1'b1) fail("held request did not execute initially");
        @(posedge clk);
        #1;
        if (execute_pulse !== 1'b0 || temporal_integrity_fault !== 1'b1)
            fail("held duplicate was not blocked after first acceptance");
        @(posedge clk);
        #1;
        if (temporal_fault_latched !== 1'b1) fail("held duplicate did not latch temporal fault");

        // Exhaust one complete modulo-256 transaction epoch and verify wrap.
        reset_guard();
        for (i = 0; i < 256; i = i + 1)
            issue_valid(i[7:0]);
        if (expected_command_seq !== 8'h00) fail("sequence did not wrap from ff to 00");
        issue_valid(8'h00);
        if (expected_command_seq !== 8'h01) fail("post-wrap zero command did not execute");

        // Live isolated corruption of either stored representation fails closed.
        reset_guard();
        force dut.expected_seq_q = 8'h01;
        #1;
        if (sequence_state_integrity_fault !== 1'b1 || temporal_integrity_fault !== 1'b1)
            fail("primary sequence-store corruption was not detected");
        if (execute_pulse !== 1'b0) fail("primary sequence-store corruption allowed execution");
        @(posedge clk);
        #1;
        if (temporal_fault_latched !== 1'b1) fail("primary sequence-store corruption did not latch");
        release dut.expected_seq_q;

        reset_guard();
        force dut.expected_seq_inv_q = 8'hfe;
        #1;
        if (sequence_state_integrity_fault !== 1'b1 || temporal_integrity_fault !== 1'b1)
            fail("inverse sequence-store corruption was not detected");
        if (execute_pulse !== 1'b0) fail("inverse sequence-store corruption allowed execution");
        @(posedge clk);
        #1;
        if (temporal_fault_latched !== 1'b1) fail("inverse sequence-store corruption did not latch");
        release dut.expected_seq_inv_q;

        $display("PASS: PRIME-HW v0.7 sequence-pair space=65536 valid=256 invalid=65280 temporal scenarios=7 isolated sequence-store fault classes=2");
        $finish(0);
    end
endmodule
