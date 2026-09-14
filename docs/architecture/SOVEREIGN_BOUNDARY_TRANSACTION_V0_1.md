# Worldshepherd Sovereign Boundary Transaction v0.1

Status: **IMPLEMENTED IN SOFTWARE on feature branch; repository CI remains the integration authority**

## 1. The transaction

Worldshepherd now has one explicit software transaction that composes policy, human authority, signed authority custody, exact-action binding, execution evidence, persistent provenance, and replay:

```text
DOMAIN REQUEST
     |
     v
BoundaryAction
     |
     | canonical SHA-256
     v
OPA-style PDP decision ------------------------------+
     |                                               |
     | decision + policy revision + action digest    |
     v                                               |
SBK envelope                                         |
     |                                               |
     +-- DENY ------------------------> REJECTED      |
     |                                               |
     +-- ESCALATE --> HUMAN APPROVAL                 |
     |                  |                            |
     |                  v                            |
     |             AUTHORIZED                        |
     |                  |                            |
     |                  v                            |
     |       PRIME SENTINEL Ed25519 assertion        |
     |       bound to envelope/action/actor/          |
     |       maturity/scope/policy/approval           |
     |                  |                            |
     |                  v                            |
     |          PRIME-bound envelope                 |
     |                  |                            |
     |          exact runtime action?                |
     |             /          \                      |
     |           no            yes                   |
     |           |              |                    |
     |      FAIL CLOSED         v                    |
     |                      EXECUTION                 |
     |                           |                    |
     |                           v                    |
     |                    SARA event outbox           |
     |                    AT_LEAST_ONCE               |
     |                           |                    |
     |                           v                    |
     |                    ECHO persistence            |
     |                 dedupe + reconciliation        |
     |                           |                    |
     |                           v                    |
     +-------------------- evidence graph / replay ---+
```

The governing principle is:

> **A side effect is not trusted because a model proposed it, because policy said `allow`, because a human approved it, or because a signing key authorized it in isolation. It is executable only when the entire purpose-bound chain agrees on the same exact action and evidence maturity.**

## 2. OPA-compatible PDP/PEP binding

`sovereign_boundary_authority.py` adds `OpaBoundDecision`, which carries:

- `decision`: allow / deny / escalate / audit_only;
- `decision_id`;
- policy package and revision;
- human-approval and MFA requirements;
- returned constraints;
- audit directives;
- the exact `action_digest` evaluated by policy.

`boundary_policy_from_opa()` fails closed when:

- the policy decision digest does not match the SBK action;
- required MFA has not been explicitly satisfied by the PEP;
- OPA returned constraints that the PEP has not explicitly enforced.

Human approval is different: it is not treated as pre-satisfied. It becomes a state transition inside SBK so the resulting approval reference and approver can be preserved in the evidence chain.

This implements the repository's existing PDP/PEP design rather than turning OPA into an executor.

## 3. Purpose-bound PRIME SENTINEL authorization

The existing PRIME SENTINEL requalification assertion remains unchanged. SBK adds a separate effect-specific assertion:

`WS-PRIME-SENTINEL-EFFECT-AUTHZ-V0.1`

The Ed25519-signed assertion binds:

- authorization ID;
- SBK envelope ID;
- actor;
- exact action digest;
- evidence/effect scope;
- capability maturity status;
- policy revision;
- human-approval reference;
- signing key ID;
- issue and expiry timestamps;
- nonce.

The verifier additionally checks:

- known signing key;
- key revocation state;
- issuance skew;
- expiry;
- Ed25519 signature;
- exact equality with the current verified SBK envelope.

The verified signing-key SHA-256 fingerprint is then bound back into the SBK envelope as custody evidence.

## 4. Physical effects now require two independent authority layers

SBK v0.1 requires every physical effect to be human gated.

The branch now adds a second runtime requirement:

> **A physical action cannot enter EXECUTED/FAILED state without a purpose-bound PRIME authorization reference and signing-key fingerprint.**

Therefore this sequence is insufficient:

```text
policy allow -> human approval -> physical execute
```

The required sequence is:

```text
policy allow/escalate
        -> human approval
        -> purpose-bound PRIME signed assertion
        -> exact runtime-action match
        -> physical execution record
```

This is defense in depth: policy, human authority, cryptographic authority, action identity, evidence maturity, and runtime execution are separate checks.

## 5. Evidence maturity remains independent of authority

Authority cannot promote maturity.

Examples enforced by SBK:

- `SIMULATED_ONLY` cannot cross into `PHYSICAL` effect scope.
- `REQUIRES_LAB_VALIDATION + LAB_TEST + PHYSICAL` may enter a human/PRIME-gated lab execution path but remains `REQUIRES_LAB_VALIDATION`.
- `OPERATIONAL + PHYSICAL` requires `PROVEN_INTERNALLY` plus a physical-validation reference before the authority chain can complete.

Running an experiment is not proof that the experiment succeeded, and authorization to run it is not evidence of capability maturity.

## 6. ECHO round-trip semantics

SBK queues parameter-minimized evidence through the existing SARA event outbox.

The end-to-end test exercises the real existing software semantics:

1. SBK creates a `sovereign_boundary_transition` event.
2. The existing outbox assigns a stable `SARA-EVENT-*` ID.
3. Delivery declares `AT_LEAST_ONCE` semantics.
4. The existing ECHO SQLite store ingests the audit event.
5. Re-delivery of identical semantic content is deduplicated.
6. SARA/ECHO reconciliation classifies the event `MATCHED`.
7. ECHO health remains clean.

No exactly-once claim is made. Stable IDs plus semantic hashes make at-least-once replay observable and reconcilable.

## 7. Parameter minimization

Raw action parameters remain inside the sealed SBK envelope and are bound by `action_digest`.

The ECHO transition event intentionally carries only the minimum forensic set, including:

- envelope digest;
- action digest;
- actor/domain/action/resource metadata;
- effect scope;
- capability status;
- environment;
- policy revision/disposition;
- human approval reference;
- PRIME authorization reference;
- PRIME signing-key fingerprint;
- source and execution evidence references;
- claims boundary.

This reduces propagation of potentially sensitive parameters without losing the ability to prove which exact action was evaluated and executed.

## 8. Replay and authority graph

`sovereign_boundary_replay.py` adds two complementary views.

### Mission replay adapter

SBK transitions become ordinary `MissionEvent` records with stable sequence and elapsed-time fields, so they can enter the existing deterministic mission-replay path.

### Evidence graph

Each terminal governed effect can be represented as nodes for:

- bound action;
- policy decision;
- SBK envelope;
- human approval;
- PRIME SENTINEL authorization;
- execution result.

Edges record relations such as:

- policy `governs` action;
- action is `bound_by_digest` to envelope;
- human approval `authorizes` envelope;
- PRIME assertion provides `purpose_bound_authorization`;
- envelope `produces` execution result.

The graph intentionally excludes raw action parameters.

## 9. Cross-domain consequence

The same transaction can be reused by thin adapters for:

- AI/tool calls;
- administrative automation;
- APNT source or mode changes;
- digital-twin updates;
- manufacturing parameter changes;
- autonomous-platform actions;
- programmable physical boundaries;
- other future effectors.

The domain adapter owns domain semantics. SBK owns common authority semantics.

That separation is the architectural point:

> **Worldshepherd's reusable core is the governed-effect transaction, not any specific model, cloud, robot, RF surface, or solver.**

## 10. Software test milestone

`test_sovereign_boundary_end_to_end.py` provides an integration proof across the existing codebase:

```text
OPA-bound decision
  -> SBK AWAITING_HUMAN_APPROVAL
  -> recorded CRE1AWS approval
  -> generated Ed25519 PRIME assertion
  -> signature and purpose verification
  -> PRIME authorization bound into envelope
  -> exact-action execution
  -> SARA outbox
  -> ECHO store
  -> duplicate delivery deduplication
  -> SARA/ECHO MATCHED reconciliation
  -> replay sequence
  -> evidence graph
```

The physical-scope test uses a deliberately non-operational lab-validation transaction with `energy_enabled=false`; it verifies authority mechanics only. It is not a physical actuation or performance test.

Additional negative tests verify:

- OPA action-digest mismatch fails closed;
- PRIME authorization cannot be reused for a changed actor/envelope;
- physical execution remains blocked after human approval if PRIME authorization has not been bound.

## 11. Claims boundary

This work supports the claim:

**IMPLEMENTED IN SOFTWARE:** a common, hash-bound, policy/human/cryptographic authority and evidence transaction exists on the feature branch and is covered by repository tests, subject to CI completion and review.

It does not support claims of:

- operational physical safety;
- weapon-system authorization;
- flightworthiness;
- RF/EM performance;
- physical programmable-boundary performance;
- FedRAMP, CMMC, ATO, IL5, or IL6 authorization;
- classified-system suitability;
- legally admissible evidence;
- exactly-once event delivery.

Those remain separate validation and accreditation problems.

## 12. Next assurance gates

The next high-value work is narrower, not broader:

1. persist PRIME effect-authorization consumption/replay state transactionally rather than only binding a verified short-lived assertion;
2. bind PRIME configuration-custody / software-release digests into the authorization assertion;
3. add DDIL pre-authorization scope + expiry + rejoin reconciliation;
4. emit a machine-readable CI qualification bundle for the complete governed-effect transaction;
5. after those software gates, add one benign instrumented hardware lab interface whose only purpose is to prove that the PEP physically refuses unauthorized commands.

That last step must remain a safety/authority validation experiment, not a capability-performance claim.
