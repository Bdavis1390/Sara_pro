`timescale 1ns/1ps

module prime_hw_shadow_state_guard (
    input  logic [6:0] shadow_state,
    output logic       shadow_valid,
    output logic [2:0] semantic_state
);
    localparam logic [6:0] SH_RESET       = 7'b0000001;
    localparam logic [6:0] SH_BOOT_LOCKED = 7'b0000010;
    localparam logic [6:0] SH_VERIFY      = 7'b0000100;
    localparam logic [6:0] SH_OPERATIONAL = 7'b0001000;
    localparam logic [6:0] SH_DEGRADED    = 7'b0010000;
    localparam logic [6:0] SH_SAFE        = 7'b0100000;
    localparam logic [6:0] SH_RECOVERY    = 7'b1000000;

    localparam logic [2:0] ST_RESET       = 3'd0;
    localparam logic [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam logic [2:0] ST_VERIFY      = 3'd2;
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;
    localparam logic [2:0] ST_DEGRADED    = 3'd4;
    localparam logic [2:0] ST_SAFE        = 3'd5;
    localparam logic [2:0] ST_RECOVERY    = 3'd6;

    always_comb begin
        shadow_valid = 1'b1;
        semantic_state = ST_SAFE;

        unique case (shadow_state)
            SH_RESET:       semantic_state = ST_RESET;
            SH_BOOT_LOCKED: semantic_state = ST_BOOT_LOCKED;
            SH_VERIFY:      semantic_state = ST_VERIFY;
            SH_OPERATIONAL: semantic_state = ST_OPERATIONAL;
            SH_DEGRADED:    semantic_state = ST_DEGRADED;
            SH_SAFE:        semantic_state = ST_SAFE;
            SH_RECOVERY:    semantic_state = ST_RECOVERY;
            default: begin
                shadow_valid = 1'b0;
                semantic_state = ST_SAFE;
            end
        endcase
    end
endmodule
