# PRIME-HW v0.1 Reference RTL

**Status:** DRAFT / RTL REFERENCE / SIMULATION ONLY / BLOCK MERGE  
**Date:** 2026-09-12

## Purpose

PRIME-HW v0.1 is a deliberately small hardware policy and mission-assurance controller intended to test whether a bounded authorization state machine can independently enforce fail-safe lifecycle behavior around a host compute system.

It does not implement an AI accelerator, general-purpose processor, mission planner, cryptographic primitive, network stack, or autonomous command generator.

The governing rule is:

`requester proposes -> bounded hardware state/policy gate evaluates -> allow or deny -> external evidence system records outcome`

## Implemented state model

The first synthesizable SystemVerilog reference implements:

- `RESET`
- `BOOT_LOCKED`
- `VERIFY`
- `OPERATIONAL`
- `DEGRADED`
- `SAFE`
- `RECOVERY`

The design defaults protected requests to denied unless an explicitly permitted state and authorization input are simultaneously valid.

### Operational authorization

An ordinary protected request may be allowed only when:

- state is `OPERATIONAL`;
- request is valid;
- request authorization is asserted;
- boot remains verified;
- policy remains valid;
- no fatal fault is active;
- health is not degraded.

### Degraded authorization

`DEGRADED` uses a separate `degraded_request_authorized` input. Ordinary authorization does not automatically carry into degraded operation.

### Safe-state behavior

`SAFE` cannot be exited without explicit `recovery_authorized` and absence of a fatal fault. A loss of verified boot/policy while operating also resolves to `SAFE`.

Unknown/illegal encoded states resolve to `SAFE` through the default transition branch.

## Testbench

`tb_prime_hw_policy_controller.sv` checks:

- reset and boot-lock denial;
- verification-state denial;
- authorized operational allow;
- unauthorized operational denial;
- explicit degraded-mode authorization separation;
- fatal-fault transition to `SAFE`;
- inability to leave `SAFE` without recovery authorization;
- bounded recovery path;
- policy-loss fail-safe behavior.

## Explicitly not implemented yet

- cryptographic signature verification;
- key storage/root-of-trust primitives;
- monotonic hardware counters;
- anti-rollback policy storage;
- hash-chain/audit storage;
- secure boot implementation;
- tamper sensors;
- clock/voltage fault detectors;
- formal property proofs;
- AXI/PCIe/UCIe interfaces;
- FPGA board integration;
- ASIC implementation;
- post-quantum accelerators;
- hardware security certification.

Those remain later gates. The current boolean inputs (`boot_verified`, `policy_valid`, and authorization signals) represent trust-boundary interfaces whose producers must be separately implemented and verified.

## Claims boundary

Before focused CI completes, the maximum allowed claim is:

**IMPLEMENTED AS DRAFT SYNTHESIZABLE REFERENCE RTL / VALIDATION PENDING**

After a successful compiler/simulation CI gate, the maximum claim becomes:

**PROVEN INTERNALLY IN RTL SIMULATION FOR THE V0.1 STATE/AUTHORIZATION SCOPE**

The following remain **NOT CURRENTLY CLAIMED**:

- fabricated Worldshepherd silicon;
- FPGA hardware validation;
- Intel/SkyWater/GlobalFoundries qualification;
- radiation hardness;
- timing closure or power/area performance;
- FIPS, Common Criteria, NSA, DoD, CMMC, or safety certification;
- UCIe compliance;
- production security;
- operational autonomy authorization.

## Next gates

1. Compile and execute the exact-head SystemVerilog testbench.
2. Add assertions/formal properties for illegal-state, authorization, recovery, and fail-safe invariants.
3. Add explicit policy-version/anti-rollback interface and reference model.
4. Add immutable event-transition identifiers for ECHO/SARA audit correlation.
5. Add a simple memory-mapped register interface only after the state semantics remain stable.
6. Synthesize against a selected FPGA target and record actual LUT/register/timing/power evidence.
7. Conduct independent design/security review.
8. Consider mature-node MPW migration only after measured FPGA evidence justifies it.

No merge, fabrication, foundry engagement claim, or production readiness claim is authorized by this reference alone.
