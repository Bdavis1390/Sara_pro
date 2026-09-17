# Worldshepherd Sovereign Boundary Transaction v0.1

Status: **IMPLEMENTED IN SOFTWARE on feature branch; repository CI remains the integration authority**

## 1. The transaction

Worldshepherd now has one explicit software transaction that composes policy, human authority, signed authority custody, exact-action binding, one-time execution authority, same-host cross-process serialization, execution evidence, persistent provenance, and replay:

```text
DOMAIN REQUEST
     |
     v
BoundaryAction
     |
     | canonical SHA-256
     v
OPA-style PDP decision
     |
     v
SBK envelope
     |
     +-- DENY ------------------------> REJECTED
     |
     +-- ESCALATE --> HUMAN APPROVAL
     |                  |
     |                  v
     |             AUTHORIZED
     |                  |
     |                  v
     |       PRIME SENTINEL Ed25519 assertion
     |       bound to envelope/action/actor/
     |       maturity/scope/policy/approval
     |                  |
     |                  v
     |        durable VERIFIED -> CLAIMED
     |                  |
     |         exact runtime action?
     |             /          \
     |           no            yes
     |           |              |
     |      FAIL CLOSED         v
     |                POSIX process-shared lock
     |                          |
     |                          v
     |                 CLAIMED -> INVOKING
     |                          |
     |                          v
     |                 PHYSICAL PEP / executor
     |                      /           \
     |                known result    uncertain
     |                     |              |
     |                     v              v
     |                  CONSUMED      INDETERMINATE
     |                     |
     |                     v
     |              SARA event outbox
     |               AT_LEAST_ONCE
     |                     |
     |                     v
     |              ECHO persistence
     |           dedupe + reconciliation
     |                     |
     +--------------- evidence graph / replay
```

The governing principle is:

> **A side effect is executable only when policy, evidence maturity, human authority, signed authority custody, one-time execution state, and the exact runtime action agree on the same effect.**

## 2. Exact-action policy binding

`OpaBoundDecision` carries the policy decision, policy revision, returned requirements/constraints, audit directives, and the exact `action_digest` evaluated by policy.

`boundary_policy_from_opa()` fails closed when:

- the PDP digest does not match the proposed SBK action;
- required MFA has not been explicitly satisfied;
- returned policy constraints have not been explicitly enforced by the PEP.

Human approval remains a separate SBK state transition so the approver and approval reference remain observable evidence rather than an implicit Boolean.

## 3. Purpose-bound PRIME SENTINEL authority

The effect-specific Ed25519 assertion `WS-PRIME-SENTINEL-EFFECT-AUTHZ-V0.1` binds:

- authorization ID;
- envelope ID;
- actor;
- exact action digest;
- effect/evidence scope;
- capability maturity status;
- policy revision;
- human-approval reference;
- signing-key ID;
- issue and expiry timestamps;
- nonce.

Verification checks known/revoked keys, issuance skew, expiry, signature validity, and exact equality with the current sealed SBK envelope. The verified signing-key fingerprint is bound back into the envelope as custody evidence.

## 4. One-time authority state machine

The durable PRIME effect-authority lifecycle is:

```text
VERIFIED -> CLAIMED -> INVOKING -> CONSUMED
                         |
                         +-------> INDETERMINATE
```

Important semantics:

- `VERIFIED` means cryptographic authority has been checked but not reserved for execution.
- `CLAIMED` binds one execution ID to the authorization.
- `INVOKING` is the durable point of no safe automatic replay.
- `CONSUMED` means an explicit result was recorded and authority cannot be reused.
- `INDETERMINATE` means the system cannot prove whether an effect occurred and must not auto-retry the authorization.

Authorization expiry is rechecked when crossing `CLAIMED -> INVOKING`, not merely when the signed assertion is first verified.

## 5. Same-host cross-process serialization

`DurableStore` now serializes registry mutations with two nested controls:

```text
threading.RLock
      +
POSIX fcntl.flock(LOCK_EX)
      +
validated read / derive / write
      +
atomic replace + fsync
```

Every cooperating `DurableStore` process that points to the same local data directory contends on the same secured `.registry.lock` file.

This closes the process race in which two independent workers could otherwise both observe `CLAIMED` before either persisted `INVOKING`.

The claim is intentionally narrow: this is same-host POSIX advisory locking. It is not distributed consensus and is not claimed for independent authority stores, bypass writers, or filesystems whose locking semantics have not been validated.

## 6. Physical PEP semantics

The physical PEP performs this sequence:

1. verify the sealed SBK envelope;
2. recompute and compare the exact runtime action digest;
3. verify PRIME authorization/execution references;
4. acquire the durable process-shared `CLAIMED -> INVOKING` fence;
5. invoke exactly one executor callback;
6. convert an explicit executor result into a terminal SBK envelope;
7. persist `INVOKING -> CONSUMED` together with the pending SARA/ECHO event in one registry transaction.

If an exception or durable-finalization failure occurs after the invocation fence, the authorization moves to `INDETERMINATE` best-effort and is unsafe to retry automatically.

The local registry transaction does **not** make an external device side effect atomically commit with the filesystem.

## 7. Evidence maturity remains independent of authority

Authority cannot promote maturity.

Examples enforced by SBK:

- `SIMULATED_ONLY` cannot cross into `PHYSICAL` effect scope.
- `REQUIRES_LAB_VALIDATION + LAB_TEST + PHYSICAL` remains `REQUIRES_LAB_VALIDATION` after an authorized experiment.
- `OPERATIONAL + PHYSICAL` requires `PROVEN_INTERNALLY` plus a physical-validation reference before authority can complete.

Running an experiment is not proof of capability, and authorization to run it is not evidence of success.

## 8. ECHO semantics

SBK emits parameter-minimized evidence through the existing SARA outbox.

The transaction preserves the repository's actual semantics:

1. SBK creates a `sovereign_boundary_transition` event.
2. The outbox assigns a stable `SARA-EVENT-*` ID.
3. Delivery is `AT_LEAST_ONCE`.
4. ECHO ingests the audit event.
5. identical semantic redelivery is deduplicated;
6. SARA/ECHO reconciliation can classify the event `MATCHED`.

No exactly-once event-delivery claim is made.

## 9. Cross-process adversarial proofs

Two dedicated tests now exercise process-shared serialization.

`test_storage_cross_process.py` launches two independent processes that intentionally widen a lost-update race window against one registry. Both updates must survive, proving serialized read/derive/write behavior for cooperating processes.

`test_sovereign_boundary_pep_cross_process.py` holds process A inside a benign de-energized executor after A has persisted `INVOKING`. Process B then attempts the identical authorization/execution ID from an independent process. B must fail before its executor callback can emit an `entered` event. A subsequently completes and the ledger ends in `CONSUMED`.

The existing same-process tests continue to cover runtime mutation, expiry-at-use, executor ambiguity, durable reload, replay refusal, and evidence generation.

## 10. Cross-domain consequence

Thin adapters can reuse the same authority transaction for:

- AI/tool calls;
- administrative automation;
- APNT source/mode changes;
- digital-twin updates;
- manufacturing parameter changes;
- autonomous-platform actions;
- programmable physical boundaries;
- future effectors.

The domain adapter owns domain semantics. SBK owns common authority/evidence semantics.

> **Worldshepherd's reusable core is the governed-effect transaction, not any specific model, cloud, robot, RF surface, or solver.**

## 11. Claims boundary

Subject to current-head CI and review, this work supports:

**IMPLEMENTED IN SOFTWARE:** a hash-bound policy/human/cryptographic authority transaction with durable one-time effect authorization, same-host POSIX cross-process invocation serialization, parameter-minimized evidence, ECHO reconciliation, and replay/evidence-graph adapters.

It does not establish:

- physical safety certification;
- flightworthiness;
- RF/EM or propulsion performance;
- DoD authorization, ATO, FedRAMP, CMMC, IL5, or IL6 authorization;
- classified-system suitability;
- legally admissible evidence;
- multi-host/distributed mutual exclusion;
- hardware-enforced non-replay;
- exactly-once physical actuation; or
- exactly-once event delivery.

## 12. Next assurance gates

The next high-value work is now sharply defined:

1. bind release/configuration-custody digests into every physical-effect authorization;
2. add DDIL preauthorization scope, expiry, revocation, and rejoin reconciliation;
3. generate a machine-readable CI qualification bundle for the entire governed-effect transaction;
4. design a device-side challenge/grant interlock so stale or replayed host commands are rejected by the effector boundary itself;
5. only after those software gates, connect a benign de-energized or low-energy lab fixture whose first job is to prove refusal behavior rather than performance.
