# Worldshepherd Frontier AI Safety Assurance (WS-FASA) v1.0 Foundation

## Purpose

WS-FASA binds AI capability growth to independently enforceable authorization, evidence, monitoring, and human-control gates.

Core invariant:

> No increase in autonomous capability may outrun demonstrated control, containment, observability, provenance, and human authority.

This is an engineering readiness baseline. It is not a certification or a guarantee of safety.

## Current implementation

The current feature-branch implementation includes:

1. A six-level capability ladder and fail-closed policy evaluator.
2. Version-bound capability-registry records with an invariant that authorization cannot exceed assessed capability.
3. An authoritative protected capability-registry namespace in durable SARA state.
4. PRIME SENTINEL Ed25519 approval leases bound to model/version, capability level, action, target environment, policy, evaluation, assurance evidence, expiry, signer, and nonce.
5. Short approval lifetimes with F5 approval leases disabled.
6. A protected approval-state namespace with VERIFIED-to-CONSUMED transitions and replay resistance.
7. A transactional runtime admission gate that reads authoritative capability state, evaluates the action, and consumes any required approval before returning ALLOW.
8. Tamper-evident admission evidence containing the decision inputs, disposition, reasons, approval identity, provenance/monitoring state, and a SHA-256 decision digest.
9. Generic administrative registry writes are blocked from mutating FASA capability or approval namespaces.
10. F5 execution is an immutable WS-FASA v1 denial rather than a configurable policy option.

The runtime gate performs admission control only. It does not itself execute an external operation.

## Capability ladder

| Level | Operational meaning | Default posture |
|---|---|---|
| F0 | Text/reasoning only | Bounded execution |
| F1 | Read-only tools/data | Logged, scoped access |
| F2 | Reversible bounded tool actions | Automatic eligibility only when all gates pass |
| F3 | Consequential external action | Verified human/PRIME approval required |
| F4 | Persistent or high-risk autonomous capability | Approval plus current safety case and independent review |
| F5 | Capability with potentially catastrophic consequences | DENY invariant in WS-FASA v1 |

## Implemented invariants

1. Model identity and version must match the authoritative capability registry.
2. Capability evaluation must be current.
3. Maximum authorized capability cannot exceed assessed capability.
4. Requested capability cannot exceed assessed or authorized levels.
5. Required ECHO provenance must remain enabled.
6. Required OVERWATCH monitoring must remain enabled.
7. Self-authorization is denied.
8. AI-directed modification of governing safety policy is denied.
9. Monitoring suppression is denied.
10. Unbounded agent creation is denied.
11. F4 requires a current safety case and independent review.
12. Approval-gated ALLOW decisions require a valid PRIME-signed lease bound to the exact action and active evaluation context.
13. Approval state is consumed transactionally before an approval-gated ALLOW is returned.
14. FASA capability and approval namespaces cannot be changed through the generic administrative registry endpoint.
15. F5 execution and F5 approval leases are disabled by WS-FASA v1 invariant.

## Separation of authority

```text
Human authority
    -> PRIME policy / approval trust root
    -> authoritative FASA capability state
    -> SARA transactional admission gate
    -> ECHO evidence/provenance
    -> OVERWATCH independent monitoring
    -> continue / constrain / contain / terminate
```

The evaluated model must not possess unilateral authority over policy, approval issuance, capability-evaluation custody, evidence custody, independent monitoring, or its own promotion state.

## Validation state

The WS-FASA feature branch has passed the repository's SARA Verified Local v1 CI gate after the runtime-custody additions. That gate includes unit/API testing, software-supply-chain evidence generation, PRE qualification generation, Compose validation, deployment verification, destructive backup/restore exercise, operational snapshot capture, release-identity verification, and release-evidence indexing.

This supports an internal software-implementation claim. It does not convert CI evidence into external certification, formal verification, or field validation.

## Claims boundary

Supported narrow claim:

> IMPLEMENTED IN SOFTWARE — fail-closed frontier-capability classification, protected capability custody, PRIME-bound approval leases, transactional approval consumption, and tamper-evident admission-decision evidence have been implemented and exercised in repository CI.

Not claimed: prevention of catastrophic outcomes, proof of alignment, independent third-party validation, production-grade external key custody, immutable off-system evidence retention, field validation, formal certification, or safe F5 execution.

## Next gates

Phase 4: bind every FASA admission decision and approval-consumption transition into the ECHO signed evidence chain, including decision digest, transition ID, authorization ID, capability evaluation ID, and release identity.

Phase 5: independent OVERWATCH tripwires and deterministic containment-state transitions whose authority cannot be suppressed by the evaluated model.

Phase 6: governed capability-evaluation ingestion with independently attributable evaluator identity and signed/attested evaluation provenance.

Phase 7: adversarial evaluation of policy adherence, privilege boundaries, approval replay resistance, persistence behavior, monitoring integrity, evidence integrity, and out-of-distribution behavior.

Phase 8: independent external review before any claim of production safety assurance or certification readiness.

## Promotion rule

A capability level is never inherited automatically by a new model version. Every version requires its own authoritative registry entry, current evaluation evidence, and authorization ceiling. A changed evaluation receives a new evaluation identifier and cannot silently reuse the prior evaluation identity.
