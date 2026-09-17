`timescale 1ns/1ps

module prime_hw_policy_controller_hardened (
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
    output logic       state_integrity_fault,
    output logic [2:0] state_code
);
    // Seven 8-bit state codewords selected with pairwise Hamming distance >= 4.
    // Therefore a 1-, 2-, or 3-bit corruption of a valid codeword cannot alias
    // another valid codeword. The guard maps every non-codeword to semantic SAFE.
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

    logic [7:0] state_q;
    logic [7:0] state_d;
    logic       state_valid;
    logic [2:0] semantic_state;

    prime_hw_state_code_guard state_guard (
        .encoded_state(state_q),
        .state_valid(state_valid),
        .semantic_state(semantic_state)
    );

    always_comb begin
        // Fail-safe default: any invalid encoded state converges to encoded SAFE
        // at the next active edge.
        state_d = ST_SAFE_CODE;

        if (state_valid) begin
            unique case (semantic_state)
                ST_RESET: begin
                    state_d = ST_BOOT_LOCKED_CODE;
                end

                ST_BOOT_LOCKED: begin
                    state_d = ST_BOOT_LOCKED_CODE;
                    if (fatal_fault)
                        state_d = ST_SAFE_CODE;
                    else if (boot_verified)
                        state_d = ST_VERIFY_CODE;
                end

                ST_VERIFY: begin
                    state_d = ST_VERIFY_CODE;
                    if (fatal_fault || !policy_valid)
                        state_d = ST_SAFE_CODE;
                    else if (boot_verified && policy_valid) begin
                        if (health_degraded)
                            state_d = ST_DEGRADED_CODE;
                        else
                            state_d = ST_OPERATIONAL_CODE;
                    end
                end

                ST_OPERATIONAL: begin
                    state_d = ST_OPERATIONAL_CODE;
                    if (fatal_fault || !policy_valid || !boot_verified)
                        state_d = ST_SAFE_CODE;
                    else if (health_degraded)
                        state_d = ST_DEGRADED_CODE;
                end

                ST_DEGRADED: begin
                    state_d = ST_DEGRADED_CODE;
                    if (fatal_fault || !policy_valid || !boot_verified)
                        state_d = ST_SAFE_CODE;
                    else if (!health_degraded)
                        state_d = ST_OPERATIONAL_CODE;
                end

                ST_SAFE: begin
                    state_d = ST_SAFE_CODE;
                    if (recovery_authorized && !fatal_fault)
                        state_d = ST_RECOVERY_CODE;
                end

                ST_RECOVERY: begin
                    state_d = ST_RECOVERY_CODE;
                    if (fatal_fault)
                        state_d = ST_SAFE_CODE;
                    else if (boot_verified && policy_valid) begin
                        if (health_degraded)
                            state_d = ST_DEGRADED_CODE;
                        else
                            state_d = ST_OPERATIONAL_CODE;
                    end else begin
                        state_d = ST_BOOT_LOCKED_CODE;
                    end
                end

                default: state_d = ST_SAFE_CODE;
            endcase
        end
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            state_q <= ST_RESET_CODE;
        else
            state_q <= state_d;
    end

    always_comb begin
        // Fail closed before interpreting any semantic state.
        allow = 1'b0;
        deny = request_valid;
        safe_state = 1'b1;
        state_integrity_fault = !state_valid;
        state_code = ST_SAFE;

        if (state_valid) begin
            safe_state = (semantic_state == ST_SAFE);
            state_code = semantic_state;

            unique case (semantic_state)
                ST_OPERATIONAL: begin
                    if (request_valid && request_authorized &&
                        boot_verified && policy_valid &&
                        !fatal_fault && !health_degraded) begin
                        allow = 1'b1;
                        deny = 1'b0;
                    end
                end

                ST_DEGRADED: begin
                    if (request_valid && degraded_request_authorized &&
                        boot_verified && policy_valid && !fatal_fault) begin
                        allow = 1'b1;
                        deny = 1'b0;
                    end
                end

                default: begin
                    allow = 1'b0;
                end
            endcase
        end
    end
endmodule
