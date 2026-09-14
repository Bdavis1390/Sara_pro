# Worldshepherd Sovereign Boundary Kernel (SBK) v0.1

Status: **IMPLEMENTED IN SOFTWARE on feature branch; pending repository CI and review**

## 1. Purpose

The Sovereign Boundary Kernel is a domain-neutral execution contract between a requested effect and the mechanism that can cause that effect.

It turns the existing Worldshepherd governance doctrine into a machine-enforced transaction:

> sense / propose -> classify evidence maturity -> evaluate policy -> bind the exact action -> obtain required human approval -> execute only the bound action -> emit provenance -> replay and audit

SBK is deliberately small. It does not replace SARA, PRIME SENTINEL, ECHO SENTINEL LINK, OVERWATCH, the OPA policy envelope, the event outbox, qualification evidence, or domain solvers. It is the **common boundary contract** that composes those systems.

## 2. Why this is a new architectural layer

Worldshepherd already contains two mature directions that had been evolving separately:

1. **Governed execution and evidence**
   - SARA orchestration and audit
   - bounded autonomy policy
   - OPA PDP / PEP separation
   - PRIME SENTINEL authorization and custody
   - ECHO persistence, reconciliation, checkpoints, and replay
   - qualification and claims-control states

2. **Programmable physical/simulation boundaries**
   - programmable-boundary synthetic benchmark
   - NSB solver ladder
   - actuator and finite-geometry electromagnetic forward models
   - material / field-control research with explicit validation gates

SBK makes the shared lifecycle explicit. AI tools, autonomous platforms, APNT decisions, digital twins, manufacturing actions, and programmable physical boundaries can all use the same authorization/evidence semantics without pretending that the underlying physics or maturity is the same.

## 3. Core invariant

**Authorization never upgrades evidence maturity.**

An action may be authorized only within the effect scope justified by its current capability status and policy context.

Examples:

- `SIMULATED_ONLY + SIMULATION` may be executed as a simulation.
- `SIMULATED_ONLY + PHYSICAL` fails closed.
- `REQUIRES_LAB_VALIDATION + PHYSICAL + LAB_TEST` remains human-gated and does not become `PROVEN_INTERNALLY` because it ran.
- `PHYSICAL + OPERATIONAL` requires `PROVEN_INTERNALLY`, a physical validation reference, and explicit human approval in v0.1.

This converts Worldshepherd claims control from a documentation convention into a runtime safety property.

## 4. Exact-action binding

The policy-evaluated action is canonicalized and SHA-256 bound as `action_digest`.

The runtime executor must present the same action object at execution time. If any parameter changes after policy evaluation, the digest changes and execution is refused with a re-evaluation requirement.

This closes a common agentic-control gap:

```text
policy evaluated action A
        |
        v
sha256(canonical(A))
        |
        +--------------------------+
                                   |
runtime proposes action B          |
        |                          |
        v                          v
sha256(canonical(B)) == action_digest ?
        |
   yes  |  no
        |   \
        v    -> FAIL CLOSED / RE-EVALUATE
    execute
```

## 5. Envelope model

Each SBK envelope binds:

- actor
- domain
- action type
- resource
- exact parameters (inside the sealed envelope)
- effect scope
- capability status
- execution environment
- mission/session context
- network state
- provenance / model / agent metadata
- source evidence references
- policy revision and disposition
- human-approval requirement and approval reference
- action digest
- execution result
- claims boundary
- envelope digest

The entire envelope is separately SHA-256 bound by `envelope_digest`.

## 6. State machine

```text
PROPOSED
   |
   +-- policy DENY ------------------------------> REJECTED
   |
   +-- policy AUDIT_ONLY ------------------------> PROPOSED (non-executable)
   |
   +-- ALLOW / ESCALATE + approval required ----> AWAITING_HUMAN_APPROVAL
   |                                                  |
   |                                                  +-- approval --> AUTHORIZED
   |
   +-- ALLOW + no approval required --------------> AUTHORIZED
                                                       |
                                                       +-- exact action match --> EXECUTED
                                                       |
                                                       +-- executor failure ---> FAILED
                                                       |
                                                       +-- action mismatch ----> FAIL CLOSED / RE-EVALUATE
```

In v0.1, every physical effect requires explicit human approval.

## 7. PDP / PEP relationship

SBK preserves the repository's existing OPA architecture:

- **PDP** evaluates policy.
- **SBK envelope** records the policy decision and binds the exact requested action.
- **PEP / executor** checks SBK authorization immediately before effect.
- **ECHO / audit** receives a parameter-minimized evidence event.

SBK is not itself a policy language. It is the enforcement and evidence contract between decision and effect.

## 8. Evidence minimization

The ECHO/outbox transition payload intentionally excludes raw action parameters.

It records instead:

- `envelope_digest`
- `action_digest`
- domain / action / resource metadata
- effect scope
- capability status
- environment
- policy revision/disposition
- state
- approval reference
- evidence references

This supports forensic binding without unnecessarily copying sensitive parameters into every event channel.

The complete action remains bound by `action_digest` in the sealed envelope.

## 9. Existing outbox semantics

SBK transitions can be queued through the existing SARA event outbox.

The outbox remains `AT_LEAST_ONCE`; downstream ECHO consumers must deduplicate using the stable outbox event ID. SBK does not claim exactly-once delivery.

## 10. First cross-domain adapter: programmable boundary benchmark

The first adapter intentionally uses the repository's existing **synthetic programmable-boundary benchmark**, because that benchmark already has aggressive claims controls.

The adapter:

1. verifies the benchmark report digest;
2. requires `SIMULATED_ONLY` capability status;
3. selects a named scenario;
4. creates an SBK action with `EvidenceScope.SIMULATION`;
5. binds the benchmark report digest into the action parameters;
6. permits execution only as simulation;
7. fails closed if the same action is relabeled as physical.

This is an architecture proof, not a physical electromagnetic validation claim.

## 11. Executable proof

From `deployments/sara_verified_local_v1` after installation:

```bash
ws-sovereign-boundary-demo
```

or:

```bash
python -m worldshepherd_sara.sovereign_boundary_kernel_cli
```

The proof performs four things:

1. runs the deterministic programmable-boundary simulation benchmark;
2. converts one scenario into an SBK action;
3. executes the hash-bound action through an authorized simulation envelope;
4. attempts to promote that `SIMULATED_ONLY` action to a physical effect and confirms the kernel blocks it.

The expected result includes:

```json
{
  "benchmark_capability_status": "SIMULATED_ONLY",
  "terminal_state": "EXECUTED",
  "envelope_verified": true,
  "physical_promotion_blocked": true
}
```

The exact SHA-256 values vary because the envelope contains timestamps, while the underlying benchmark report remains deterministic.

## 12. Security properties established by v0.1 software tests

The test suite is designed to establish only these software properties:

- exact action binding;
- envelope tamper detection;
- fail-closed runtime-action mutation;
- fail-closed simulation-to-physical maturity promotion;
- explicit human gate for physical effects;
- operational-physical requirement for proven status plus physical-validation reference;
- lab-test preservation of `REQUIRES_LAB_VALIDATION` status;
- event-parameter minimization;
- integration with the existing at-least-once event outbox;
- adapter binding to the existing programmable-boundary benchmark digest.

It does **not** establish:

- physical safety certification;
- RF/EM performance;
- flightworthiness;
- DoD authorization;
- FedRAMP/CMMC compliance;
- classified-system suitability;
- autonomous weapons approval;
- exactly-once event delivery;
- legal admissibility of evidence.

## 13. Domain expansion pattern

New domains should add thin adapters rather than fork governance logic.

```text
                    WORLD SHEPHERD SBK
                           |
        +------------------+------------------+
        |                  |                  |
      AI/TOOLS           APNT              DIGITAL TWIN
        |                  |                  |
        +------------------+------------------+
                           |
                 common policy/evidence
                           |
        +------------------+------------------+
        |                  |                  |
   MANUFACTURING      ROBOTICS/EDGE     PROGRAMMABLE BOUNDARY
```

Each adapter is responsible for:

- translating a domain request into `BoundaryAction`;
- assigning the correct evidence scope and capability status;
- referencing qualification evidence;
- presenting the exact same action to the executor after authorization;
- returning outcome evidence.

## 14. Recommended v0.2 gates

SBK v0.2 should not simply add features. It should close specific assurance gaps:

1. **OPA decision adapter** — parse the existing OPA decision envelope directly into `BoundaryPolicyDecision`.
2. **Generic PRIME authorization** — add a purpose-bound signed authorization assertion for SBK actions instead of reusing the current requalification-specific assertion.
3. **Replay graph adapter** — emit mission-replay graph nodes for SBK envelope -> policy decision -> approval -> execution result.
4. **ECHO persistence adapter** — verify the outbox-to-ECHO round trip and reconcile the stable event ID.
5. **DDIL envelope** — encode pre-authorized degraded-state scope, expiry, and rejoin reconciliation.
6. **Configuration custody binding** — include software/configuration digests from PRIME passport/custody evidence.
7. **Signed envelope option** — add Ed25519 signing for the envelope digest using managed key custody; do not treat a plain digest as a signature.
8. **Release evidence** — generate one machine-readable qualification bundle proving all v0.1 invariants from CI.

## 15. Product implication

SBK changes the product boundary of Worldshepherd.

The reusable product is no longer any single AI agent, robot, solver, cloud deployment, or metasurface controller. The reusable product is the **governed effect boundary** that can sit in front of all of them.

That creates a coherent platform thesis:

> **Worldshepherd supplies a common policy, authority, maturity-control, exact-action binding, provenance, and replay kernel for heterogeneous software and physical systems. Domain-specific intelligence and actuators remain replaceable adapters.**

This thesis is defensible only to the extent supported by implemented software and evidence. v0.1 therefore makes a deliberately narrow claim: it implements and tests the common software contract and demonstrates one simulation-only cross-domain adapter. Physical and operational claims remain gated.
