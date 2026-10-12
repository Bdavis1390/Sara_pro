# PRIME-HW v0.6 — authorization-integrity witness and fail-closed voter

**Status:** STACKED DRAFT / IMPLEMENTED / EXACT-HEAD VALIDATION PENDING / BLOCK MERGE

**Dependency:** PRIME-HW v0.5 PR #238. v0.6 is a separate implementation/verification increment and does not rewrite v0.5 evidence.

## Problem addressed

v0.5 substantially hardens semantic state integrity through an 8-bit distance-coded primary state, an independently stored 7-bit one-hot shadow state, and fail-closed semantic cross-checking. That protects the controller's state representation in the declared model.

A separate safety-critical question remains: **can an authorization-output logic fault create an unsafe `allow` even when semantic state is correct?**

v0.6 adds an independently implemented authorization witness and a fail-closed voter so the final `allow` requires affirmative agreement from two authorization paths.

## Two authorization paths

### Core path

The primary vote is the `allow`/`deny` decision produced by the inherited v0.5 controller's case-structured output logic.

### Witness path

`prime_hw_authorization_witness.sv` independently recomputes the expected authorization decision as a direct Boolean predicate over:

- semantic state;
- state-integrity status;
- boot trust;
- policy validity;
- health degradation;
- fatal fault;
- request validity;
- ordinary authorization; and
- degraded authorization.

For OPERATIONAL, witness allow requires a valid request, valid boot/policy trust, no state-integrity or fatal fault, non-degraded health, and ordinary authorization.

For DEGRADED, witness allow requires a valid request, valid boot/policy trust, no state-integrity or fatal fault, and degraded authorization.

All other states deny.

The witness is deliberately written with direct Boolean predicates rather than the controller's case-structured output implementation. This is representation/implementation diversity at RTL, not proof of physical design independence.

## Fail-closed voter

`prime_hw_authorization_voter.sv` compares core and witness allow/deny votes.

`authorization_integrity_fault` asserts if either allow votes or deny votes disagree.

Final permission is:

- request valid;
- core allow vote asserted;
- witness allow vote asserted;
- no state-integrity fault;
- no authorization vote disagreement; and
- no previously latched authorization-integrity event.

A mismatch can therefore remove permission but cannot create permission in the declared voter model.

Final `deny` is recomputed after voting as `request_valid && !allow`.

## Sticky disagreement escalation

`prime_hw_authorization_fault_latch.sv` latches any authorization-integrity disagreement until reset.

The sticky latch is ORed into the v0.5 core's fatal-fault input. Consequences in the declared synchronous model are:

1. disagreement is detected combinationally;
2. final `allow` is blocked immediately;
3. the disagreement is captured at the next active edge;
4. the sticky event continues to block authorization even if the transient corruption disappears; and
5. the underlying semantic controller converges to SAFE on the following active edge.

This is a reset-cleared fail-safe policy. v0.6 does not silently resume authorization after a detected authorization-cone inconsistency.

## Exhaustive pre-synthesis contracts

The focused RTL regression exhausts:

- **2,048 witness truth cases**: all eight possible 3-bit state values × all 256 combinations of the eight Boolean witness inputs;
- **128 voter truth cases**: all combinations of the seven voter inputs; and
- **four live preserved-rail fault classes**: core allow stuck high, witness allow stuck high, core deny stuck low, and witness deny stuck low from a clean operational deny baseline.

Each live rail disagreement must deny immediately, assert authorization-integrity fault, latch the event, remain fail-closed after the forced rail is released, and escalate the semantic controller to SAFE.

## Post-synthesis authorization-cone audit

The four authorization rails are preserved in the Yosys evidence architecture:

- `core_allow_vote`;
- `witness_allow_vote`;
- `core_deny_vote`; and
- `witness_deny_vote`.

The sticky authorization-fault latch is also preserved.

`check_synthesized_authorization_cone.py` inspects the generated Yosys JSON and requires:

1. all four preserved vote rails exist as distinct synthesized scalar net bits;
2. final `allow` transitive fan-in contains both independent allow-vote rails;
3. final `allow` transitive fan-in contains the sticky authorization-fault latch;
4. the authorization-integrity-fault cone contains all four allow/deny vote rails; and
5. final `deny` depends on the voted allow cone.

This is structural evidence about the recorded Yosys netlist. It does **not** establish physical gate separation, placement/routing independence, clock/power independence, or immunity to common-mode optimization in a different vendor flow.

## Bounded formal contract

The v0.6 formal harness proves, within the recorded horizon:

- complete symbolic authorization-witness truth behavior;
- complete symbolic fail-closed voter truth behavior;
- voter disagreement/state-integrity/sticky-fault states cannot produce `allow`;
- final `allow` implies both independent allow votes;
- standalone authorization-fault latch persistence after a symbolic transient event;
- nominal v0.6 behavior matches the exact v0.5 reference for semantic state, `allow`, `deny`, `safe_state`, and state-integrity status; and
- nominal unmutated operation does not spuriously assert or latch authorization-integrity fault.

Twelve formal cover witnesses require reachability of:

- all seven semantic states;
- ordinary witness allow;
- degraded witness allow;
- authorization-path disagreement;
- upstream state-integrity suppression; and
- sticky authorization-fault latch activation.

## Claims boundary

If all exact-head gates pass, the maximum intended machine-supported claim is:

> **PROVEN INTERNALLY IN THE DECLARED RTL/YOSYS-STRUCTURAL/BOUNDED-FORMAL MODEL THAT THE V0.6 INDEPENDENT AUTHORIZATION WITNESS MATCHES THE DECLARED POLICY PREDICATE ACROSS ALL 2,048 EXHAUSTED WITNESS INPUT CASES; THE FAIL-CLOSED VOTER MATCHES ITS DECLARED FUNCTION ACROSS ALL 128 INPUT COMBINATIONS; THE FOUR DECLARED ISOLATED PRESERVED-VOTE-RAIL DISAGREEMENT CLASSES DENY IMMEDIATELY, LATCH, AND ESCALATE TOWARD SEMANTIC SAFE; THE RECORDED YOSYS EVIDENCE NETLIST RETAINS BOTH ALLOW-VOTE RAILS IN THE FINAL ALLOW FAN-IN AND ALL FOUR VOTE RAILS IN THE AUTHORIZATION-INTEGRITY-FAULT FAN-IN; AND NOMINAL EXTERNAL POLICY/STATE BEHAVIOR MATCHES THE V0.5 REFERENCE WITHIN THE RECORDED FORMAL HORIZON.**

This does **not** establish:

- common-mode faults that corrupt core and witness consistently;
- faults in the final output pin/pad, external actuator wiring, or downstream interlock;
- physical independence of the two authorization paths;
- physical fault-injection or radiation qualification;
- asynchronous glitch filtering or delay-insensitive voting;
- clock/reset/power-domain fault tolerance;
- FPGA configuration-memory immunity;
- ASIC timing/PPA/DFT/foundry qualification;
- cryptographic root-of-trust assurance; or
- safety/security certification.

The formal SMT path lowers asynchronous resets with `async2sync; dffunmap`; this remains a formal-model boundary, not a separate asynchronous-reset-equivalence proof.

## Next substantial gate

After v0.6 exact-head machine verification and independent review, the next assurance increment should move the fault campaign deeper into synthesized control logic: identify safety-critical combinational/state-transition nodes in the evidence netlist, inject controlled stuck-at/inversion mutations at selected cones, measure detection and fail-close coverage, and use residual escapes to justify selective duplication, temporal checking, or hardened implementation constraints. Physical fault campaigns remain a later device/partner validation stage.

Keep this PR stacked/draft and **BLOCK MERGE** until exact-head CI is green, evidence is preserved, independent review is clean, the dependency stack is reconciled, and CRE1AWS explicitly authorizes incorporation.
