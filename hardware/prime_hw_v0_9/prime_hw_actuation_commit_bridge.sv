`timescale 1ns/1ps

module prime_hw_actuation_commit_bridge #(
    parameter integer ACK_TIMEOUT_CYCLES = 16
) (
    input  wire        clk,
    input  wire        reset_n,
    input  wire        upstream_execute_pulse,
    input  wire [7:0]  command_seq,
    input  wire [63:0] command_digest,
    input  wire        actuator_ack_valid,
    input  wire        actuator_ack_success,
    input  wire [7:0]  actuator_ack_seq,
    input  wire [63:0] actuator_ack_digest,
    output wire        actuator_issue_pulse,
    output wire        actuator_commit_pulse,
    output wire        actuation_pending,
    output wire [7:0]  pending_seq,
    output wire [63:0] pending_digest,
    output wire [7:0]  pending_age,
    output wire        actuation_integrity_fault,
    output wire        actuation_fault_latched,
    output wire        bridge_state_integrity_fault
);
    localparam [7:0] TIMEOUT_LAST_AGE = ACK_TIMEOUT_CYCLES - 1;

    // Every safety-relevant stored field has a complementary representation.
    // This proves a logical representation-diversity contract only; it does not
    // establish physical placement or common-mode fault independence.
    (* keep *) reg        pending_valid_q;
    (* keep *) reg        pending_valid_inv_q;
    (* keep *) reg [7:0]  pending_seq_q;
    (* keep *) reg [7:0]  pending_seq_inv_q;
    (* keep *) reg [63:0] pending_digest_q;
    (* keep *) reg [63:0] pending_digest_inv_q;
    (* keep *) reg [7:0]  pending_age_q;
    (* keep *) reg [7:0]  pending_age_inv_q;
    (* keep *) reg        actuation_fault_latched_q;
    (* keep *) reg        actuation_fault_latched_inv_q;

    (* keep *) reg actuator_issue_pulse_q;
    (* keep *) reg actuator_commit_pulse_q;

    wire [81:0] state_primary;
    wire [81:0] state_inverse;
    wire bridge_state_valid;
    wire ack_tuple_match;
    wire unsolicited_ack;
    wire bad_pending_ack;
    wire overlapping_issue;
    wire timeout_event;
    wire fault_event;
    wire accept_new_issue;
    wire accept_commit;
    wire [7:0] next_age;

    assign state_primary = {
        actuation_fault_latched_q,
        pending_valid_q,
        pending_age_q,
        pending_seq_q,
        pending_digest_q
    };
    assign state_inverse = {
        actuation_fault_latched_inv_q,
        pending_valid_inv_q,
        pending_age_inv_q,
        pending_seq_inv_q,
        pending_digest_inv_q
    };

    prime_hw_actuation_state_guard state_guard (
        .state_primary(state_primary),
        .state_inverse(state_inverse),
        .state_valid(bridge_state_valid),
        .state_integrity_fault(bridge_state_integrity_fault)
    );

    assign ack_tuple_match =
        (actuator_ack_seq == pending_seq_q) &&
        (actuator_ack_digest == pending_digest_q);

    assign unsolicited_ack = actuator_ack_valid && !pending_valid_q;
    assign bad_pending_ack =
        actuator_ack_valid && pending_valid_q &&
        (!ack_tuple_match || !actuator_ack_success);
    assign overlapping_issue = upstream_execute_pulse && pending_valid_q;
    assign timeout_event =
        pending_valid_q &&
        !actuator_ack_valid &&
        (pending_age_q >= TIMEOUT_LAST_AGE);

    assign fault_event =
        bridge_state_integrity_fault ||
        unsolicited_ack ||
        bad_pending_ack ||
        overlapping_issue ||
        timeout_event;

    assign actuation_integrity_fault = fault_event;
    assign actuation_fault_latched =
        !bridge_state_valid || actuation_fault_latched_q;

    assign accept_new_issue =
        upstream_execute_pulse &&
        !pending_valid_q &&
        !actuator_ack_valid &&
        bridge_state_valid &&
        !actuation_fault_latched_q &&
        !fault_event;

    assign accept_commit =
        actuator_ack_valid &&
        pending_valid_q &&
        ack_tuple_match &&
        actuator_ack_success &&
        bridge_state_valid &&
        !actuation_fault_latched_q &&
        !fault_event;

    assign next_age = pending_age_q + 8'd1;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            pending_valid_q <= 1'b0;
            pending_valid_inv_q <= 1'b1;
            pending_seq_q <= 8'h00;
            pending_seq_inv_q <= 8'hff;
            pending_digest_q <= 64'h0000_0000_0000_0000;
            pending_digest_inv_q <= 64'hffff_ffff_ffff_ffff;
            pending_age_q <= 8'h00;
            pending_age_inv_q <= 8'hff;
            actuation_fault_latched_q <= 1'b0;
            actuation_fault_latched_inv_q <= 1'b1;
            actuator_issue_pulse_q <= 1'b0;
            actuator_commit_pulse_q <= 1'b0;
        end else begin
            actuator_issue_pulse_q <= 1'b0;
            actuator_commit_pulse_q <= 1'b0;

            if (fault_event) begin
                actuation_fault_latched_q <= 1'b1;
                actuation_fault_latched_inv_q <= 1'b0;
            end

            if (accept_new_issue) begin
                pending_valid_q <= 1'b1;
                pending_valid_inv_q <= 1'b0;
                pending_seq_q <= command_seq;
                pending_seq_inv_q <= ~command_seq;
                pending_digest_q <= command_digest;
                pending_digest_inv_q <= ~command_digest;
                pending_age_q <= 8'h00;
                pending_age_inv_q <= 8'hff;
                actuator_issue_pulse_q <= 1'b1;
            end else if (accept_commit) begin
                pending_valid_q <= 1'b0;
                pending_valid_inv_q <= 1'b1;
                pending_seq_q <= 8'h00;
                pending_seq_inv_q <= 8'hff;
                pending_digest_q <= 64'h0000_0000_0000_0000;
                pending_digest_inv_q <= 64'hffff_ffff_ffff_ffff;
                pending_age_q <= 8'h00;
                pending_age_inv_q <= 8'hff;
                actuator_commit_pulse_q <= 1'b1;
            end else if (
                pending_valid_q &&
                bridge_state_valid &&
                !actuation_fault_latched_q &&
                !fault_event &&
                !actuator_ack_valid
            ) begin
                pending_age_q <= next_age;
                pending_age_inv_q <= ~next_age;
            end
        end
    end

    assign actuator_issue_pulse = actuator_issue_pulse_q;
    assign actuator_commit_pulse = actuator_commit_pulse_q;
    assign actuation_pending = pending_valid_q && bridge_state_valid;
    assign pending_seq = pending_seq_q;
    assign pending_digest = pending_digest_q;
    assign pending_age = pending_age_q;
endmodule
