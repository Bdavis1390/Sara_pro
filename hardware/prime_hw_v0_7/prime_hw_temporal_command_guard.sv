`timescale 1ns/1ps

module prime_hw_temporal_command_guard (
    input  wire       clk,
    input  wire       reset_n,
    input  wire       upstream_allow,
    input  wire       request_valid,
    input  wire [7:0] command_seq,
    output wire       execute_pulse,
    output wire       temporal_integrity_fault,
    output wire       temporal_fault_latched,
    output wire       sequence_state_integrity_fault,
    output wire [7:0] expected_command_seq,
    output wire [7:0] expected_command_seq_inverse
);
    // The two sequence stores are deliberately distinct logical state elements
    // in the RTL evidence model. This is not a physical-placement-independence
    // claim; synthesis preservation is audited separately.
    (* keep *) reg [7:0] expected_seq_q;
    (* keep *) reg [7:0] expected_seq_inv_q;
    (* keep *) reg       temporal_fault_latched_q;

    wire sequence_state_valid;
    wire sequence_mismatch;
    wire temporal_fault_event;
    wire [7:0] expected_seq_next;

    prime_hw_sequence_pair_guard sequence_pair_guard (
        .expected_seq_primary(expected_seq_q),
        .expected_seq_inverse(expected_seq_inv_q),
        .sequence_state_valid(sequence_state_valid),
        .sequence_state_integrity_fault(sequence_state_integrity_fault)
    );

    assign sequence_mismatch =
        upstream_allow && request_valid && (command_seq != expected_seq_q);

    // Sequence-state corruption is fail-closed even when no command is active.
    // A bad transaction number is a temporal fault only for an upstream-approved
    // request; unauthorized traffic cannot advance or poison the sequence state.
    assign temporal_fault_event = sequence_state_integrity_fault || sequence_mismatch;
    assign temporal_integrity_fault = temporal_fault_event;

    assign execute_pulse =
        upstream_allow &&
        request_valid &&
        sequence_state_valid &&
        (command_seq == expected_seq_q) &&
        !temporal_fault_latched_q;

    assign expected_seq_next = expected_seq_q + 8'd1;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            expected_seq_q <= 8'h00;
            expected_seq_inv_q <= 8'hff;
            temporal_fault_latched_q <= 1'b0;
        end else begin
            if (temporal_fault_event)
                temporal_fault_latched_q <= 1'b1;

            if (!temporal_fault_latched_q && !temporal_fault_event && execute_pulse) begin
                expected_seq_q <= expected_seq_next;
                expected_seq_inv_q <= ~expected_seq_next;
            end
        end
    end

    assign temporal_fault_latched = temporal_fault_latched_q;
    assign expected_command_seq = expected_seq_q;
    assign expected_command_seq_inverse = expected_seq_inv_q;
endmodule
