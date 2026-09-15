`timescale 1ns/1ps

module prime_hw_policy_controller_diverse (
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
    localparam logic [7:0] P_RESET       = 8'h00;
    localparam logic [7:0] P_BOOT_LOCKED = 8'h0F;
    localparam logic [7:0] P_VERIFY      = 8'h33;
    localparam logic [7:0] P_OPERATIONAL = 8'h3C;
    localparam logic [7:0] P_DEGRADED    = 8'h55;
    localparam logic [7:0] P_SAFE        = 8'h5A;
    localparam logic [7:0] P_RECOVERY    = 8'h66;

    localparam logic [6:0] S_RESET       = 7'b0000001;
    localparam logic [6:0] S_BOOT_LOCKED = 7'b0000010;
    localparam logic [6:0] S_VERIFY      = 7'b0000100;
    localparam logic [6:0] S_OPERATIONAL = 7'b0001000;
    localparam logic [6:0] S_DEGRADED    = 7'b0010000;
    localparam logic [6:0] S_SAFE        = 7'b0100000;
    localparam logic [6:0] S_RECOVERY    = 7'b1000000;

    localparam logic [2:0] ST_RESET       = 3'd0;
    localparam logic [2:0] ST_BOOT_LOCKED = 3'd1;
    localparam logic [2:0] ST_VERIFY      = 3'd2;
    localparam logic [2:0] ST_OPERATIONAL = 3'd3;
    localparam logic [2:0] ST_DEGRADED    = 3'd4;
    localparam logic [2:0] ST_SAFE        = 3'd5;
    localparam logic [2:0] ST_RECOVERY    = 3'd6;

    // Keep the two representation-diverse state stores explicitly visible in
    // the vendor-neutral evidence netlist. This supports structural auditing
    // of the RTL implementation; it is not a physical-placement guarantee.
    (* keep *) logic [7:0] primary_state_q;
    logic [7:0] primary_state_d;
    (* keep *) logic [6:0] shadow_state_q;
    logic [6:0] shadow_state_d;
    logic       primary_valid;
    logic       shadow_valid;
    logic [2:0] semantic_state;

    prime_hw_dual_state_guard dual_guard (
        .primary_state(primary_state_q),
        .shadow_state(shadow_state_q),
        .primary_valid(primary_valid),
        .shadow_valid(shadow_valid),
        .state_integrity_fault(state_integrity_fault),
        .semantic_state(semantic_state)
    );

    // Primary transition path: distance-coded representation.
    always_comb begin
        primary_state_d = P_SAFE;
        if (!state_integrity_fault) begin
            unique case (semantic_state)
                ST_RESET: primary_state_d = P_BOOT_LOCKED;
                ST_BOOT_LOCKED: begin
                    primary_state_d = P_BOOT_LOCKED;
                    if (fatal_fault) primary_state_d = P_SAFE;
                    else if (boot_verified) primary_state_d = P_VERIFY;
                end
                ST_VERIFY: begin
                    primary_state_d = P_VERIFY;
                    if (fatal_fault || !policy_valid) primary_state_d = P_SAFE;
                    else if (boot_verified && policy_valid)
                        primary_state_d = health_degraded ? P_DEGRADED : P_OPERATIONAL;
                end
                ST_OPERATIONAL: begin
                    primary_state_d = P_OPERATIONAL;
                    if (fatal_fault || !policy_valid || !boot_verified) primary_state_d = P_SAFE;
                    else if (health_degraded) primary_state_d = P_DEGRADED;
                end
                ST_DEGRADED: begin
                    primary_state_d = P_DEGRADED;
                    if (fatal_fault || !policy_valid || !boot_verified) primary_state_d = P_SAFE;
                    else if (!health_degraded) primary_state_d = P_OPERATIONAL;
                end
                ST_SAFE: begin
                    primary_state_d = P_SAFE;
                    if (recovery_authorized && !fatal_fault) primary_state_d = P_RECOVERY;
                end
                ST_RECOVERY: begin
                    primary_state_d = P_RECOVERY;
                    if (fatal_fault) primary_state_d = P_SAFE;
                    else if (boot_verified && policy_valid)
                        primary_state_d = health_degraded ? P_DEGRADED : P_OPERATIONAL;
                    else primary_state_d = P_BOOT_LOCKED;
                end
                default: primary_state_d = P_SAFE;
            endcase
        end
    end

    // Shadow transition path: one-hot representation, written separately so
    // state storage and transition encoding are representation-diverse at RTL.
    always_comb begin
        shadow_state_d = S_SAFE;
        if (!state_integrity_fault) begin
            unique case (shadow_state_q)
                S_RESET: shadow_state_d = S_BOOT_LOCKED;
                S_BOOT_LOCKED: begin
                    shadow_state_d = S_BOOT_LOCKED;
                    if (fatal_fault) shadow_state_d = S_SAFE;
                    else if (boot_verified) shadow_state_d = S_VERIFY;
                end
                S_VERIFY: begin
                    shadow_state_d = S_VERIFY;
                    if (fatal_fault || !policy_valid) shadow_state_d = S_SAFE;
                    else if (boot_verified && policy_valid)
                        shadow_state_d = health_degraded ? S_DEGRADED : S_OPERATIONAL;
                end
                S_OPERATIONAL: begin
                    shadow_state_d = S_OPERATIONAL;
                    if (fatal_fault || !policy_valid || !boot_verified) shadow_state_d = S_SAFE;
                    else if (health_degraded) shadow_state_d = S_DEGRADED;
                end
                S_DEGRADED: begin
                    shadow_state_d = S_DEGRADED;
                    if (fatal_fault || !policy_valid || !boot_verified) shadow_state_d = S_SAFE;
                    else if (!health_degraded) shadow_state_d = S_OPERATIONAL;
                end
                S_SAFE: begin
                    shadow_state_d = S_SAFE;
                    if (recovery_authorized && !fatal_fault) shadow_state_d = S_RECOVERY;
                end
                S_RECOVERY: begin
                    shadow_state_d = S_RECOVERY;
                    if (fatal_fault) shadow_state_d = S_SAFE;
                    else if (boot_verified && policy_valid)
                        shadow_state_d = health_degraded ? S_DEGRADED : S_OPERATIONAL;
                    else shadow_state_d = S_BOOT_LOCKED;
                end
                default: shadow_state_d = S_SAFE;
            endcase
        end
    end

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            primary_state_q <= P_RESET;
            shadow_state_q <= S_RESET;
        end else begin
            primary_state_q <= primary_state_d;
            shadow_state_q <= shadow_state_d;
        end
    end

    always_comb begin
        allow = 1'b0;
        deny = request_valid;
        safe_state = 1'b1;
        state_code = ST_SAFE;

        if (!state_integrity_fault) begin
            safe_state = (semantic_state == ST_SAFE);
            state_code = semantic_state;

            unique case (semantic_state)
                ST_OPERATIONAL: begin
                    if (request_valid && request_authorized && boot_verified &&
                        policy_valid && !fatal_fault && !health_degraded) begin
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
                default: allow = 1'b0;
            endcase
        end
    end
endmodule
