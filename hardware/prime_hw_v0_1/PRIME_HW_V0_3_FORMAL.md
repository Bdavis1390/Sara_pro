# PRIME-HW v0.3 bounded formal safety verification

**Status:** STACKED DRAFT / STRENGTHENED FORMAL HARNESS / EXACT-HEAD VALIDATION PENDING / BLOCK MERGE

**Dependency:** PRIME-HW v0.2 PR #200, which is stacked on v0.1 PR #186.

**Claims boundary:** bounded formal safety-property verification of the existing PRIME-HW v0.1 controller only. This increment does not modify controller RTL.

## Purpose

The v0.1 controller has passed bounded RTL simulation. The v0.2 verification increment has passed vendor-neutral Yosys synthesis plus exhaustive declared transition/authorization matrix simulation. v0.3 adds a symbolic bounded-proof layer over the same controller RTL.

The formal harness treats control and authorization inputs as symbolic and establishes one reset edge followed by released reset. It then asks the solver to prove declared safety/transition properties across all input assignments within the recorded proof horizon.

## Declared safety properties

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

## Reachability and anti-vacuity witnesses

The harness declares 12 cover statements. CI requires all 12 to be reached inside the same 20-step bounded environment before the cover gate can pass.

Four principal-state witnesses require reachability of:

- OPERATIONAL;
- DEGRADED;
- SAFE; and
- RECOVERY.

Eight assertion-family witnesses require the environment to exercise:

- an allowed OPERATIONAL request;
- an allowed DEGRADED request;
- active-state trust/fatal loss reaching SAFE;
- OPERATIONAL health degradation reaching DEGRADED;
- healthy trusted DEGRADED recovery reaching OPERATIONAL;
- SAFE stickiness with recovery not authorized;
- SAFE stickiness with recovery authorized but a fatal fault present; and
- authorized non-fatal SAFE recovery reaching RECOVERY.

These witnesses reduce the risk that guarded assertions pass only because their antecedents are unreachable. They do not establish that the property set is semantically complete.

## Tooling and formal-model treatment

Focused CI uses:

- Yosys 0.33 formal front-end and SMT2 backend;
- `yosys-smtbmc`;
- Z3;
- a recorded 20-step proof horizon;
- a separate cover run; and
- exact-head evidence custody.

The native controller uses an asynchronous-reset flip-flop. Yosys 0.33's SMT2 backend does not directly accept the resulting `$adff`, so the **formal-only** netlist is lowered using `async2sync; dffunmap` before `write_smt2`.

That transformation is part of the proof model and is recorded in the evidence artifact. The controller RTL is not modified. A successful bounded proof is **not** a separate proof that the lowering is behaviorally equivalent for every asynchronous-reset timing case.

The evidence artifact records the exact tested commit, tool/solver context, proof horizon, formal clock treatment, reset lowering, declared/reached cover counts, source/harness/SMT hashes, and proof/cover logs.

## Important boundary

A green bounded SMT proof is **not** equivalent to:

- unbounded theorem proving;
- a separate asynchronous-reset-equivalence proof;
- complete temporal verification of all future controller extensions;
- FPGA board validation;
- timing closure or PPA characterization;
- side-channel analysis;
- cryptographic root-of-trust verification;
- fault-injection qualification;
- ASIC/foundry qualification;
- radiation validation; or
- FIPS/Common Criteria/NSA/DoD certification.

No controller feature or security maturity is upgraded merely because this verification harness exists.

## Claims state

Before a green exact-head proof plus all 12 cover witnesses:

**IMPLEMENTED / FORMAL REVALIDATION PENDING**

Maximum claim after a green exact-head gate:

**PROVEN INTERNALLY FOR THE DECLARED PRIME-HW v0.1 SAFETY PROPERTIES WITHIN THE RECORDED 20-STEP BOUNDED SMT HORIZON, WITH ASSERTION-FAMILY REACHABILITY WITNESSES**

A clean independent review remains a separate incorporation gate.

## Incorporation gate

This PR must remain stacked/draft and block merge until:

1. exact-head native RTL regression succeeds;
2. exact-head bounded assertion proof succeeds;
3. all 12 cover/reachability witnesses are reached;
4. evidence artifact is preserved;
5. independent review is clean when review capacity is available; and
6. CRE1AWS explicitly authorizes incorporation.
