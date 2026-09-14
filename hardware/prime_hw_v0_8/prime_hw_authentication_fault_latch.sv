`timescale 1ns/1ps

module prime_hw_authentication_fault_latch (
    input  wire clk,
    input  wire reset_n,
    input  wire authentication_integrity_fault,
    output reg  authentication_fault_latched
);
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            authentication_fault_latched <= 1'b0;
        else if (authentication_integrity_fault)
            authentication_fault_latched <= 1'b1;
    end
endmodule
