# PRIME-HW v0.2 synthesis and transition-matrix verification

**Status:** STACKED DRAFT / VALIDATION PENDING / BLOCK MERGE  
**Dependency:** PRIME-HW v0.1 PR #186  
**Claims boundary:** vendor-neutral RTL synthesis and exhaustive declared transition/authorization matrix simulation only.

## Purpose

PRIME-HW v0.1 established a small synthesizable policy-controller reference with bounded RTL simulation. This stacked increment tests whether that exact reference:

1. passes a vendor-neutral Yosys synthesis/check flow; and
2. satisfies the complete declared input matrix for its principal OPERATIONAL, DEGRADED, and SAFE transition/authorization rules.

This is an FPGA-readiness precursor. It is not an FPGA implementation, formal proof, timing closure, physical validation, security certification, or ASIC result.

## Transition matrix

The new testbench exhausts all 16 combinations of:

- `fatal_fault`;
- `policy_valid`;
- `boot_verified`; and
- `health_degraded`

from both OPERATIONAL and DEGRADED states.

Expected OPERATIONAL priority:

1. fatal fault or loss of policy/boot trust -> SAFE;
2. otherwise health degradation -> DEGRADED;
3. otherwise remain OPERATIONAL.

Expected DEGRADED priority:

1. fatal fault or loss of policy/boot trust -> SAFE;
2. otherwise recovered health -> OPERATIONAL;
3. otherwise remain DEGRADED.

The SAFE matrix exhausts recovery authorization versus fatal fault and requires SAFE to remain latched unless recovery is explicitly authorized with no fatal fault.

## Authorization matrix

The testbench exhausts the three-input request truth table in OPERATIONAL and DEGRADED:

- `request_valid`;
- `request_authorized`; and
- `degraded_request_authorized`.

OPERATIONAL uses only ordinary authorization. DEGRADED uses only degraded authorization. This checks that one permission class cannot silently substitute for the other.

## Synthesis gate

The focused CI installs Yosys and Icarus Verilog, then:

- compiles and runs the existing PRIME-HW v0.1 simulation;
- compiles and runs the new exhaustive declared-state matrix;
- synthesizes `prime_hw_policy_controller` with Yosys;
- executes Yosys structural `check`;
- writes a vendor-neutral JSON netlist; and
- preserves synthesis output as a CI evidence artifact.

No vendor-specific constraints, clock timing, placement, routing, utilization target, power model, or hardware programming step is included.

## Claims state

Before a green exact-head gate and clean review:

**IMPLEMENTED / VALIDATION PENDING**

Maximum post-gate claim:

**PROVEN INTERNALLY IN VENDOR-NEUTRAL RTL SYNTHESIS AND DECLARED TRANSITION-MATRIX SIMULATION FOR THE PRIME-HW v0.1 CONTROLLER SCOPE**

Still not claimed:

- formal verification;
- exhaustive proof over arbitrary temporal sequences;
- FPGA board validation;
- timing closure;
- PPA characterization;
- cryptographic root of trust;
- anti-rollback hardware;
- PCIe/AXI/UCIe integration;
- ASIC/foundry readiness;
- radiation tolerance; or
- FIPS/Common Criteria/NSA/DoD certification.

## Incorporation gate

This PR is stacked on #186 and must remain blocked until its focused CI/review are clean and the underlying v0.1 dependency is incorporated or otherwise explicitly authorized by CRE1AWS.
