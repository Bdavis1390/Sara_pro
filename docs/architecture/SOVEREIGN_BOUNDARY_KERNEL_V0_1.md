# Worldshepherd Sovereign Boundary Kernel (SBK) v0.1

Status: **IMPLEMENTED IN SOFTWARE on feature branch; pending current-head repository CI and review**

## 1. Purpose

The Sovereign Boundary Kernel is a domain-neutral execution contract between a requested effect and the mechanism that can cause that effect.

It turns the Worldshepherd governance doctrine into a machine-enforced transaction:

> sense / propose -> classify evidence maturity -> evaluate policy -> bind exact action -> obtain required human authority -> bind purpose-specific cryptographic authority -> reserve one execution -> cross a one-way invocation fence -> execute only the bound action -> emit provenance -> reconcile and replay

SBK does not replace SARA, PRIME SENTINEL, ECHO SENTINEL LINK, OVERWATCH, OPA policy, the event outbox, qualification evidence, or domain solvers. It is the **common governed-effect boundary** that composes them.

## 2. Architectural unification

Worldshepherd contains two directions that had previously evolved largely independently:

1. governed execution and evidence — SARA orchestration, bounded autonomy, OPA PDP/PEP separation, PRIME authority/custody, ECHO persistence/reconciliation, replay, qualification and claims control;
2. programmable simulation/physical boundaries — synthetic programmable-boundary benchmarks, NSB solver ladders, actuator/finite-geometry forward models, and material/field-control research with explicit validation gates.

SBK provides the common transaction lifecycle without pretending those domains share the same physical maturity.

## 3. Core invariants

### 3.1 Authorization never upgrades evidence maturity

- `SIMULATED_ONLY + SIMULATION` may execute as simulation.
- `SIMULATED_ONLY + PHYSICAL` fails closed.
- `REQUIRES_LAB_VALIDATION + PHYSICAL + LAB_TEST` remains human/PRIME gated and remains `REQUIRES_LAB_VALIDATION` after execution.
- `PHYSICAL + OPERATIONAL` requires `PROVEN_INTERNALLY`, a physical-validation reference, and explicit human authority in v0.1.

### 3.2 Authority is conjunctive, not singular

A physical effect is not executable merely because policy says allow, a human approves, or a signing key authorizes in isolation. The exact action, evidence maturity, policy decision, human authority, PRIME authority, one-time execution state, and invocation state must all agree.

### 3.3 INVOKING is the point of no safe automatic replay

A physical authorization has a durable lifecycle:

```text
VERIFIED -> CLAIMED -> INVOKING -> CONSUMED
                         |
                         +-------> INDETERMINATE
```

Only the caller that successfully persists `CLAIMED -> INVOKING` may enter the physical executor.

## 4. Exact-action binding

The policy-evaluated action is canonicalized and SHA-256 bound as `action_digest`.

The executor must present the same action at runtime. Any post-policy parameter mutation changes the digest and requires re-evaluation.

```text
policy evaluates action A
        |
        v
sha256(canonical(A))
        |
runtime presents action B
        |
        v
sha256(canonical(B)) == action_digest ?
       / \
     yes  no
      |    \
      v     -> FAIL CLOSED / RE-EVALUATE
  authority chain
```

## 5. Envelope model

Each SBK envelope binds at least:

- actor;
- domain / action type / resource;
- exact parameters inside the sealed envelope;
- effect scope and capability maturity;
- execution environment and network state;
- mission/session context;
- model/agent/source evidence provenance;
- policy revision and disposition;
- human-approval requirement/reference;
- PRIME authorization reference and signing-key fingerprint;
- one-time execution claim reference;
- action digest;
- execution result/evidence;
- claims boundary;
- envelope digest.

Raw action parameters are not copied into routine ECHO/outbox evidence events.

## 6. Policy and human authority

SBK preserves the PDP/PEP separation:

- OPA-compatible PDP evaluates policy;
- SBK binds the exact action and the policy decision;
- human approval is recorded as an explicit state transition when required;
- the PEP rechecks the exact action immediately before effect;
- ECHO receives parameter-minimized evidence.

OPA is not treated as the executor.

## 7. PRIME purpose-bound effect authority

`WS-PRIME-SENTINEL-EFFECT-AUTHZ-V0.1` is a short-lived Ed25519 assertion bound to:

- authorization/envelope IDs;
- actor;
- exact action digest;
- effect scope and capability status;
- policy revision;
- human-approval reference;
- key ID;
- issue/expiry times;
- nonce.

Unknown or revoked keys, signature failure, expiry, excessive future skew, or binding mismatch fail closed.

## 8. One-time execution authority

Verified PRIME authority is persisted before use.

The one-time lifecycle prevents ordinary replay:

```text
VERIFIED
   |
   | reserve one execution ID
   v
CLAIMED
   |
   | exact binding + expiry recheck
   v
INVOKING
   |\
   | +--> uncertainty -> INDETERMINATE
   |
   +----> explicit result -> CONSUMED
```

`CONSUMED` and `INDETERMINATE` authority is never automatically reusable.

## 9. Same-host cross-process invocation fence

The registry transaction now uses both an in-process `threading.RLock` and a POSIX `fcntl.flock(LOCK_EX)` on a secured `.registry.lock` file.

For cooperating Worldshepherd processes using the same local authoritative data directory, the `CLAIMED -> INVOKING` transition therefore has one serialized winner.

A second process attempting the same authorization sees state other than `CLAIMED` and fails before entering its executor callback.

This is intentionally narrower than distributed consensus. It does not cover independent authority stores, PEP bypass, direct registry mutation outside `DurableStore`, unvalidated network filesystem semantics, or multiple hosts with separate stores.

## 10. External-effect uncertainty

An external physical device cannot be included in the same atomic filesystem transaction as the local authority ledger.

SBK therefore models uncertainty explicitly instead of claiming exactly-once actuation:

```text
INVOKING
   |
   +-- explicit known result ----------> CONSUMED
   |
   +-- executor/transport uncertainty -> INDETERMINATE
```

An `INDETERMINATE` authorization requires reconciliation and fresh authority rather than automatic retry.

## 11. Evidence semantics

The ECHO/outbox payload binds the forensic minimum, including:

- envelope/action digests;
- actor/domain/action/resource metadata;
- effect scope and capability status;
- environment;
- policy revision/disposition;
- human approval reference;
- PRIME authorization/execution claim references;
- key fingerprint;
- source/outcome evidence references;
- claims boundary.

The complete action remains bound inside the sealed envelope by `action_digest`.

The existing outbox remains `AT_LEAST_ONCE`; ECHO deduplicates stable event IDs and supports SARA/ECHO reconciliation. No exactly-once delivery claim is made.

## 12. First cross-domain adapter

The first adapter uses the deterministic synthetic programmable-boundary benchmark.

It remains strictly:

`SIMULATED_ONLY + SIMULATION`

An attempted relabel to PHYSICAL fails closed. This is an architecture proof, not a physical RF/EM performance claim.

## 13. Adversarial software proofs

The branch now includes tests for:

- exact action binding;
- envelope tamper detection;
- runtime action mutation refusal;
- simulation-to-physical maturity laundering refusal;
- explicit human gate for physical effects;
- purpose-bound PRIME Ed25519 verification;
- one-time VERIFIED/CLAIMED/INVOKING/CONSUMED lifecycle;
- expiry-at-invocation;
- `INDETERMINATE` fail-closed semantics;
- same-process duplicate invocation refusal;
- cross-process registry lost-update prevention on POSIX;
- cross-process physical-PEP duplicate invocation refusal on POSIX;
- parameter-minimized outbox evidence;
- ECHO persistence/deduplication/reconciliation;
- mission replay/evidence graph generation.

These software proofs do not establish physical safety, device firmware integrity, RF/EM performance, flightworthiness, regulatory authorization, or exactly-once physical actuation.

## 14. Cross-domain expansion pattern

New domains should add thin adapters rather than fork authority logic:

```text
                    WORLD SHEPHERD SBK
                           |
        +------------------+------------------+
        |                  |                  |
      AI/TOOLS           APNT              DIGITAL TWIN
        |                  |                  |
        +------------------+------------------+
                           |
                 common authority/evidence
                           |
        +------------------+------------------+
        |                  |                  |
   MANUFACTURING      ROBOTICS/EDGE     PROGRAMMABLE BOUNDARY
```

The adapter owns domain semantics. SBK owns the common governed-effect transaction.

## 15. Next assurance gates

The next gates are intentionally specific:

1. bind software-release/configuration-custody digests into physical effect authority;
2. add DDIL preauthorization scope, expiry, revocation, and rejoin reconciliation;
3. emit a machine-readable CI qualification bundle for the full SBK transaction;
4. add a device-side challenge/grant interlock protocol so stale/replayed host commands can be refused at the effector boundary;
5. demonstrate that protocol first on a benign de-energized or low-energy fixture whose purpose is authority/refusal validation, not capability performance;
6. treat multi-host authority as a separate distributed-systems problem requiring a single-writer authority service, transactional database/CAS, or equivalent consensus-capable design.

## 16. Product implication

SBK changes the product boundary of Worldshepherd.

The reusable product is not any individual AI model, robot, cloud substrate, solver, metasurface controller, or sensor. It is the **governed effect boundary** that can sit in front of all of them.

> **Worldshepherd supplies a common policy, human authority, cryptographic authority, maturity control, one-time invocation, exact-action binding, provenance, and replay kernel for heterogeneous software and physical systems. Domain-specific intelligence and actuators remain replaceable adapters.**

That thesis is defensible only to the extent supported by evidence. v0.1 therefore makes a deliberately bounded software claim; physical and operational claims remain gated.
