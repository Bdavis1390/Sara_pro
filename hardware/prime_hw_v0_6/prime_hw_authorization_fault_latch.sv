`timescale 1ns/1ps

module prime_hw_authorization_fault_latch (
    input  logic clk,
    input  logic reset_n,
    input  logic authorization_integrity_fault,
    output logic authorization_fault_latched
);
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            authorization_fault_latched <= 1'b0;
        else if (authorization_integrity_fault)
            authorization_fault_latched <= 1'b1;
    end
endmodule
