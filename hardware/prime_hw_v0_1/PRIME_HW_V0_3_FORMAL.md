# PRIME-HW v0.3 bounded formal safety verification

**Status:** STACKED DRAFT / IMPLEMENTED / VALIDATION PENDING / BLOCK MERGE

**Dependency:** PRIME-HW v0.2 PR #200, which is stacked on v0.1 PR #186.

**Claims boundary:** bounded formal safety-property verification of the existing PRIME-HW v0.1 controller only. This increment does not modify controller RTL.

## Purpose

The v0.1 controller has already passed bounded RTL simulation. The v0.2 verification increment has passed vendor-neutral Yosys synthesis plus exhaustive declared transition/authorization matrix simulation. v0.3 adds an independent symbolic proof layer over the same controller RTL.

The formal harness treats control and authorization inputs as symbolic and establishes one reset edge followed by released reset. It then asks the solver to prove declared safety/transition properties across all input assignments within the bounded proof horizon.

## Properties

The bounded proof checks:

1. `allow` and `deny` are never asserted simultaneously.
2. `safe_state` is asserted exactly when the controller is in `SAFE`.
3. `allow` is impossible outside `OPERATIONAL` or `DEGRADED`.
4. `OPERATIONAL` allow requires a valid request, ordinary authorization, valid boot/policy trust, no fatal fault, and non-degraded health.
5. `DEGRADED` allow requires a valid request, degraded authorization, valid boot/policy trust, and no fatal fault.
6. Loss of boot/policy trust or a fatal fault from OPERATIONAL/DEGRADED transitions to SAFE.
7. Health degradation alone from OPERATIONAL transitions to DEGRADED.
8. Restored health in a trusted DEGRADED state transitions back to OPERATIONAL.
9. SAFE remains sticky unless recovery is explicitly authorized without a fatal fault.
10. Authorized non-fatal recovery from SAFE transitions to RECOVERY.

The harness also includes cover statements for OPERATIONAL, DEGRADED, SAFE, and RECOVERY so a successful proof is not accepted without reachability evidence for principal states.

## Tooling

The focused CI uses:

- Yosys formal front-end;
- `write_smt2` symbolic model generation;
- `yosys-smtbmc`;
- Z3;
- a bounded proof horizon; and
- a separate cover run.

The exact tool versions and tested commit are recorded by CI. Proof and cover logs plus the generated SMT2 model are preserved as an evidence artifact.

## Important boundary

A green bounded SMT proof is **not** equivalent to:

- unbounded theorem proving;
- complete temporal verification of all future controller extensions;
- FPGA board validation;
- timing closure;
- side-channel analysis;
- cryptographic verification;
- fault-injection validation;
- ASIC/foundry qualification;
- radiation validation; or
- FIPS/Common Criteria/NSA/DoD certification.

No controller feature or security maturity is upgraded merely because this verification harness exists.

## Claims state

Before a green exact-head proof/cover gate:

**IMPLEMENTED / FORMAL VALIDATION PENDING**

Maximum claim after a green focused gate:

**PROVEN INTERNALLY FOR THE DECLARED PRIME-HW v0.1 SAFETY PROPERTIES WITHIN THE RECORDED BOUNDED SMT HORIZON**

A clean independent review remains a separate incorporation gate.

## Incorporation gate

This PR must remain stacked/draft and block merge until:

1. exact-head formal proof succeeds;
2. exact-head cover/reachability run succeeds;
3. evidence artifact is preserved;
4. independent review is clean when review capacity is available; and
5. CRE1AWS explicitly authorizes incorporation.
