# MAG-1.1 — PRIME Cryptographic Binding and ECHO Decision Evidence

- **Status:** stacked implementation branch / pre-merge review
- **Dependency:** MAG-1 (`feature/mag-1-trajectory-assurance`)
- **Canonical runtime:** `deployments/sara_verified_local_v1/`
- **Implemented claim state:** `IMPLEMENTED IN SOFTWARE` after exact-commit canonical CI succeeds
- **Operational effectiveness:** `REQUIRES LAB VALIDATION`

## Why MAG-1.1 exists

MAG-1 introduced a generic purpose-bound authorization envelope and trajectory-level decision gate. A generic envelope alone must not be mistaken for cryptographic proof that PRIME SENTINEL actually issued the authority.

MAG-1.1 closes that gap for one deliberately narrow, already-defined PRIME operation: `REQUALIFICATION_RELEASE`.

It also converts each MAG-1 decision into deterministic, secret-minimized evidence suitable for the existing SARA event outbox and ECHO persistence semantics.

## Security property

For the PRIME requalification path:

> MAG-1 authority is derived from a valid Ed25519-signed PRIME SENTINEL assertion that is independently verified, recorded in the PRIME authorization registry in `VERIFIED` state, current, bound to the same PRIME identity and target environment, and consistent with the recorded key fingerprint, nonce, issue time, and expiry time.

The bridge does not accept caller-selected action, purpose, scope, resource, destination, credential permission, external-egress permission, or delegation depth.

## Fixed bridge semantics

`mag1_prime_binding.py` fixes the bridge to:

- workflow: `PRIME_REQUALIFICATION_RELEASE`
- action: `REQUALIFICATION_RELEASE`
- purpose: `governed PRIME requalification release`
- scope: `prime:requalification_release`
- resource: derived from the signed PRIME identity and signed target environment
- external egress: `false`
- credential use: `false`
- maximum delegation depth: `0`

The derived authority artifact is typed `PRIME_SIGNED_AUTHORIZATION` and carries a SHA-256 digest over the canonical signed authorization material plus the signature.

## Anti-reinterpretation rule

The bridge is intentionally not a generic "signed token -> arbitrary MAG-1 permission" adapter.

A caller cannot take a valid PRIME assertion for one PRIME/environment and reinterpret it as authority to:

- publish a report;
- contact an external destination;
- use a credential;
- operate on a different PRIME;
- target a different environment;
- create a delegated authority chain; or
- substitute another action.

Changing a signed field invalidates Ed25519 verification. Changing the derived MAG-1 request produces a scope/resource/purpose mismatch. Reusing a consumed PRIME authorization fails the existing PRIME registry state check.

## Execution and one-time consumption boundary

`evaluate_prime_requalification_mag1()` establishes **eligibility**, not execution. It deliberately does not consume the authorization during evaluation.

The existing PRIME transition path remains responsible for consuming the one-time authorization as part of the governed state transition. Runtime integration must preserve this ordering:

```text
verify signed assertion
        |
verify recorded VERIFIED authorization
        |
derive fixed MAG-1 authority
        |
MAG-1 context + trajectory + autonomy decision
        |
queue decision evidence
        |
execution/state-transition boundary
        |
consume one-time PRIME authorization
        |
persist transition evidence
```

A future runtime integration must ensure that authorization consumption and the consequential transition cannot be separated by a replayable or concurrent race. Passing this unit-level bridge does not by itself prove atomic execution semantics.

## ECHO decision evidence

`mag1_evidence.py` creates `WS-MAG1-EVIDENCE-V1` records and queues them through the existing SARA event outbox using a deterministic event ID derived from:

- trajectory ID; and
- action ID.

The evidence record includes:

- action identity and side-effect class;
- MAG-1, trajectory, autonomy, and authorization dispositions;
- cumulative risk and risk delta;
- blocked-attempt count;
- deterministic policy-bundle SHA-256;
- authorization ID when present;
- authority artifact ID/type/content hash when present; and
- a count plus SHA-256 of decision reasons.

The record deliberately excludes:

- model prompts or responses;
- candidate payload contents;
- credentials;
- authorization secrets; and
- raw decision-reason text.

This is a privacy/security boundary, not merely a storage optimization.

## ECHO replay and tamper semantics

The existing ECHO store uses the stable SARA outbox event ID and semantic content hashing. MAG-1.1 tests the intended composition:

1. first decision evidence with a stable ID is stored;
2. exact semantic replay is deduplicated and increments delivery count; and
3. reuse of the same stable ID with changed semantic content raises an ECHO conflict rather than overwriting the retained evidence.

This provides deterministic replay detection for MAG-1 decision evidence without claiming a globally immutable external ledger.

## Policy binding

Every MAG-1 evidence record carries `policy_bundle_sha256`, computed from canonical JSON containing:

- the active SARA `AutonomyPolicy`;
- the active `TrajectoryGuardPolicy`;
- the context-lineage schema identifier; and
- the MAG-1 authorization schema identifier.

The hash changes when the effective policy bundle changes. It allows later evidence review to detect that two decisions were evaluated under different policy material even when their action IDs are otherwise similar.

This is a policy-content binding. It is not yet a signed policy distribution mechanism.

## Tests added by MAG-1.1

### PRIME binding tests

The suite proves the implemented bridge rejects or constrains:

- modified signed assertion fields;
- registry metadata inconsistent with the verified assertion;
- resource substitution;
- reuse of a consumed authorization; and
- action substitution.

It also exercises a valid signed, recorded, scope-correct PRIME authorization through the composite MAG-1 gate.

### ECHO evidence tests

The suite proves:

- deterministic policy hashing;
- policy-change sensitivity;
- stable trajectory/action event IDs;
- secret/payload exclusion from evidence;
- queuing through the existing at-least-once event outbox;
- exact replay deduplication in ECHO; and
- same-ID semantic tamper conflict in ECHO.

## Claims boundary

After exact-commit canonical CI passes, a precise software claim may state:

> Worldshepherd SARA implements a narrow cryptographic MAG-1 bridge for PRIME SENTINEL requalification authority and deterministic MAG-1 decision evidence compatible with SARA's existing outbox and ECHO replay/tamper semantics.

Do **not** broaden that to any of the following:

- all MAG-1 authority is cryptographically authenticated;
- all Worldshepherd actions are covered by the PRIME bridge;
- alignment is solved;
- every unauthorized trajectory will be detected or prevented;
- ECHO is an externally immutable ledger;
- the PRIME/MAG-1 execution transition is proven atomic;
- the risk weights are empirically calibrated;
- OVERWATCH containment is fully integrated; or
- production, third-party, regulatory, mission, flight, weapon, CUI, classified-system, or other certification has been established.

## Next gate — MAG-1.2

The next meaningful gate is runtime atomicity and containment, not another conceptual layer:

1. integrate MAG-1 into the actual PRIME requalification transition boundary;
2. make authorization consumption and consequential transition replay-safe under concurrency/failure;
3. persist MAG-1 decision evidence and transition evidence through ECHO in one auditable workflow;
4. add a concrete OVERWATCH pause/containment actuator only where a real runtime action boundary exists;
5. add restart/crash/fault-injection tests around the decision-consume-transition sequence;
6. add lineage/policy-state tamper tests; and
7. run repeated model-in-the-loop adversarial trials, reporting prevention, detection, false-positive, and unresolved-violation rates separately.
