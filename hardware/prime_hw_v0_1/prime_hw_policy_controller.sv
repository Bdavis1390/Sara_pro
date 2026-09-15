`timescale 1ns/1ps

module prime_hw_policy_controller (
    input  logic       clk,
    input  logic       reset_n,
    input  logic       boot_verified,
    input  logic       policy_valid,
    input  logic       health_degraded,
    input  logic       fatal_fault,
    input  logic       recovery_authorized,
    input  logic       request_valid,
    input  logic       request_authorized,
    input  logic       degraded_request_authorized,
    output logic       allow,
    output logic       deny,
    output logic       safe_state,
    output logic [2:0] state_code
);

    typedef enum logic [2:0] {
        ST_RESET       = 3'd0,
        ST_BOOT_LOCKED = 3'd1,
        ST_VERIFY      = 3'd2,
        ST_OPERATIONAL = 3'd3,
        ST_DEGRADED    = 3'd4,
        ST_SAFE        = 3'd5,
        ST_RECOVERY    = 3'd6
    } state_t;

    state_t state_q;
    state_t state_d;

    always_comb begin
        state_d = state_q;

        unique case (state_q)
            ST_RESET: begin
                state_d = ST_BOOT_LOCKED;
            end

            ST_BOOT_LOCKED: begin
                if (fatal_fault) begin
                    state_d = ST_SAFE;
                end else if (boot_verified) begin
                    state_d = ST_VERIFY;
                end
            end

            ST_VERIFY: begin
                if (fatal_fault || !policy_valid) begin
                    state_d = ST_SAFE;
                end else if (boot_verified && policy_valid) begin
                    if (health_degraded) begin
                        state_d = ST_DEGRADED;
                    end else begin
                        state_d = ST_OPERATIONAL;
                    end
                end
            end

            ST_OPERATIONAL: begin
                if (fatal_fault || !policy_valid || !boot_verified) begin
                    state_d = ST_SAFE;
                end else if (health_degraded) begin
                    state_d = ST_DEGRADED;
                end
            end

            ST_DEGRADED: begin
                if (fatal_fault || !policy_valid || !boot_verified) begin
                    state_d = ST_SAFE;
                end else if (!health_degraded) begin
                    state_d = ST_OPERATIONAL;
                end
            end

            ST_SAFE: begin
                if (recovery_authorized && !fatal_fault) begin
                    state_d = ST_RECOVERY;
                end
            end

            ST_RECOVERY: begin
                if (fatal_fault) begin
                    state_d = ST_SAFE;
                end else if (boot_verified && policy_valid) begin
                    if (health_degraded) begin
                        state_d = ST_DEGRADED;
                    end else begin
                        state_d = ST_OPERATIONAL;
                    end
                end else begin
                    state_d = ST_BOOT_LOCKED;
                end
            end

            default: begin
                state_d = ST_SAFE;
            end
        endcase
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state_q <= ST_RESET;
        end else begin
            state_q <= state_d;
        end
    end

    always_comb begin
        allow = 1'b0;
        deny = request_valid;
        safe_state = 1'b0;
        state_code = state_q;

        unique case (state_q)
            ST_OPERATIONAL: begin
                if (request_valid && request_authorized && boot_verified && policy_valid && !fatal_fault && !health_degraded) begin
                    allow = 1'b1;
                    deny = 1'b0;
                end
            end

            ST_DEGRADED: begin
                if (request_valid && degraded_request_authorized && boot_verified && policy_valid && !fatal_fault) begin
                    allow = 1'b1;
                    deny = 1'b0;
                end
            end

            ST_SAFE: begin
                safe_state = 1'b1;
            end

            default: begin
                allow = 1'b0;
            end
        endcase
    end

endmodule
