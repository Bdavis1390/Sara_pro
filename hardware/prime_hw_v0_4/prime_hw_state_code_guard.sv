`timescale 1ns/1ps

module prime_hw_state_code_guard (
    input  logic [7:0] encoded_state,
    output logic       state_valid,
    output logic [2:0] semantic_state
);
    localparam logic [7:0] ST_RESET_CODE       = 8'h00;
    localparam logic [7:0] ST_BOOT_LOCKED_CODE = 8'h0F;
    localparam logic [7:0] ST_VERIFY_CODE      = 8'h33;
    localparam logic [7:0] ST_OPERATIONAL_CODE = 8'h3C;
    localparam logic [7:0] ST_DEGRADED_CODE    = 8'h55;
    localparam logic [7:0] ST_SAFE_CODE        = 8'h5A;
    localparam logic [7:0] ST_RECOVERY_CODE    = 8'h66;

    localparam logic [2:0] ST_RESET       = 3'd0;
    localparam logic [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam logic [2:0] ST_VERIFY      = 3'd2;
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;
    localparam logic [2:0] ST_DEGRADED    = 3'd4;
    localparam logic [2:0] ST_SAFE        = 3'd5;
    localparam logic [2:0] ST_RECOVERY    = 3'd6;

    always_comb begin
        state_valid = 1'b1;
        semantic_state = ST_SAFE;

        unique case (encoded_state)
            ST_RESET_CODE:       semantic_state = ST_RESET;
            ST_BOOT_LOCKED_CODE: semantic_state = ST_BOOT_LOCKED;
            ST_VERIFY_CODE:      semantic_state = ST_VERIFY;
            ST_OPERATIONAL_CODE: semantic_state = ST_OPERATIONAL;
            ST_DEGRADED_CODE:    semantic_state = ST_DEGRADED;
            ST_SAFE_CODE:        semantic_state = ST_SAFE;
            ST_RECOVERY_CODE:    semantic_state = ST_RECOVERY;
            default: begin
                state_valid = 1'b0;
                semantic_state = ST_SAFE;
            end
        endcase
    end
endmodule
