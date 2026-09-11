# Worldshepherd Frontier AI Safety Assurance (WS-FASA) v1.0 Foundation

## Purpose

WS-FASA binds AI capability growth to independently enforceable authorization, evidence, monitoring, and human-control gates.

Core invariant:

> No increase in autonomous capability may outrun demonstrated control, containment, observability, provenance, and human authority.

This is an engineering readiness baseline. It is not a certification or a guarantee of safety.

## Phase-1 implementation

The initial `worldshepherd_sara.fasa` module provides a six-level capability ladder, a version-bound capability registry record, a fail-closed policy evaluator, mandatory provenance and monitoring gates, human-approval escalation, and a default prohibition on the highest-risk capability class.

## Capability ladder

| Level | Operational meaning | Default posture |
|---|---|---|
| F0 | Text/reasoning only | Bounded execution |
| F1 | Read-only tools/data | Logged, scoped access |
| F2 | Reversible bounded tool actions | Automatic eligibility only when all gates pass |
| F3 | Consequential external action | Human approval required |
| F4 | Persistent or high-risk autonomous capability | Human approval plus current safety case and independent review |
| F5 | Capability with potentially catastrophic consequences | DENY by default |

## Implemented invariants

1. Model identity and version must match the capability registry.
2. Capability evaluation must be current.
3. Requested capability cannot exceed assessed or authorized levels.
4. Required ECHO provenance must remain enabled.
5. Required OVERWATCH monitoring must remain enabled.
6. Self-authorization is denied.
7. AI-directed modification of governing safety policy is denied.
8. Monitoring suppression is denied.
9. Unbounded agent creation is denied.
10. F4 and above require a current safety case and independent review.
11. F5 remains disabled by default.

## Separation of authority

```text
Human authority
    -> PRIME policy authorization
    -> SARA bounded execution
    -> ECHO evidence/provenance
    -> OVERWATCH independent monitoring
    -> continue / constrain / contain / terminate
```

The evaluated model must not possess unilateral authority over policy, evidence custody, independent monitoring, or its own promotion state.

## Claims boundary

After the branch is tested, the narrow claim is:

> IMPLEMENTED IN SOFTWARE — frontier-capability classification and fail-closed policy-evaluation prototype.

Not claimed: prevention of catastrophic outcomes, proof of alignment, independent third-party validation, production-grade key custody, immutable external evidence retention, formal certification, or safe F5 execution.

## Next gates

Phase 2: short-lived capability leases with scope, expiry, resource ceilings, and revocation.

Phase 3: enforcement in the SARA execution path.

Phase 4: independent OVERWATCH tripwires and deterministic containment-state transitions.

Phase 5: bind FASA decisions and containment events into the ECHO signed evidence chain.

Phase 6: adversarial evaluation of policy adherence, privilege boundaries, persistence behavior, monitoring integrity, and out-of-distribution behavior.

## Promotion rule

A capability level is never inherited automatically by a new model version. Every version requires its own registry entry, current evaluation evidence, and authorization ceiling.
