# External technical review brief

## Purpose

This packet asks for **technical criticism, not endorsement**.

Worldshepherd SARA is being evaluated as a bounded automation/control-plane pattern: separate the party that proposes work from the mechanism that authorizes it, constrain the executable surface, record durable evidence, and make the resulting state inspectable by an operator.

The useful review result is a concrete reason to simplify, delete, redesign, or reject part of the architecture.

## Review target

Please review the narrow implementation first:

- `deployments/sara_verified_local_v1/worldshepherd_sara/app.py`
- `deployments/sara_verified_local_v1/worldshepherd_sara/auth.py`
- `deployments/sara_verified_local_v1/worldshepherd_sara/prime_sentinel_authorization.py`
- `deployments/sara_verified_local_v1/worldshepherd_sara/prime_passport_api.py`
- `deployments/sara_verified_local_v1/worldshepherd_sara/storage.py`
- `deployments/sara_verified_local_v1/worldshepherd_sara/event_outbox.py`
- `deployments/sara_verified_local_v1/tests/`
- `deployments/sara_verified_local_v1/SECURITY.md`

The rest of the repository is not required to answer the core systems questions below.

## Questions worth answering

### 1. Is there a real systems problem here?

Does separating proposal/orchestration, authorization, evidence, and operator visibility provide meaningful safety or maintainability value, or is the design creating ceremony around a problem that conventional service boundaries already solve adequately?

### 2. Are the trust boundaries real?

Specifically, can an attacker or mistaken operator:

- escalate a relay credential into administrator authority;
- mutate protected registry state through an unintended path;
- cause a signed authorization assertion to be replayed, misbound, or reused across environments;
- make the audit/evidence layer look stronger than it is;
- turn the current local-only record path into an unintended execution primitive;
- bypass fail-closed behavior when state or authorization is unavailable?

### 3. Which abstractions should be deleted?

Names are not architecture. If SARA, PRIME, ECHO, or OVERWATCH can collapse into fewer components without losing a verifiable boundary, that is preferred.

### 4. Is the evidence model useful or security theater?

The repository deliberately labels internal CI evidence as internal and unsigned where appropriate. Is that distinction sufficiently clear? What evidence would actually matter for an operator, maintainer, auditor, or downstream integrator?

### 5. Is the implementation maintainable?

Please identify unnecessary dependencies, bespoke formats, naming overhead, hidden coupling, weak failure semantics, non-determinism, or test patterns that will become expensive at scale.

## Expected reviewer behavior

The project is not asking a reviewer to accept its terminology or roadmap. Rename things mentally if that makes the design easier to judge.

A high-value response could be as short as:

- "This trust boundary is fake because X can write Y."
- "Use an existing policy engine here instead of custom code."
- "This evidence format is redundant; emit standard Z."
- "This component is unnecessary; merge it with A."
- "The replay model fails under condition B."
- "This is not a sufficiently distinct systems problem to justify a project."

Any of those is more valuable than a general expression of support.

## Partnership threshold

Partnership is **not** the first ask. A collaboration discussion only makes sense if an external reviewer concludes that at least one of the following is true:

1. the core problem is legitimate;
2. the implementation demonstrates a useful boundary;
3. a component could become reusable infrastructure;
4. the project can contribute upstream to an existing ecosystem instead of inventing its own stack.

Until then, the correct relationship is reviewer versus artifact.

## Contact posture

One concise outreach is appropriate. Repeated unsolicited follow-up is not. The repository should carry the technical argument so the message itself can stay short.
