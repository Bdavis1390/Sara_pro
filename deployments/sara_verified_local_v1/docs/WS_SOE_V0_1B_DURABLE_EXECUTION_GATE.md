# WS-SOE v0.1B Durable Execution Gate

## Scope

WS-SOE v0.1B extends the merged v0.1A software contract gate without granting Worldshepherd any new live host authority. The gate remains restricted to the harmless `demo.counter.increment` action.

v0.1B adds three bounded properties:

1. **durable replay state** — a consumed intent digest is persisted in SQLite and remains consumed across executor/store re-instantiation;
2. **transactional demo atomicity** — the in-database counter mutation and the durable execution record commit in the same `BEGIN IMMEDIATE` SQLite transaction;
3. **authority-signing separation** — a PRIME-like authority signer signs an already-created canonical `Decision` with Ed25519, while the executor receives only an expected authority identity, key ID, and public verification key.

The original five v0.1A contracts remain unchanged: `Intent`, `Decision`, `Observation`, `EvidenceReceipt`, and `ConformanceAssessment`.

## v0.1B invariants

- No demo execution occurs until the Ed25519 signature over the exact canonical `Decision` verifies under the configured public key.
- Signature verification is domain-separated with the `WS-SOE-v0.1B:Decision` signing context.
- The signed decision authority and key ID must equal the verifier's configured trust identity.
- The v0.1A exact-intent authorization and validity-window checks still apply after signature verification.
- One canonical intent digest can have at most one committed execution record in the durable store.
- Replay state survives store and executor re-instantiation.
- The demo counter mutation and execution-record insertion are one SQLite transaction. An exception between those operations rolls both back.
- Duplicate observation IDs fail the transaction and therefore cannot leave an unrecorded counter mutation.
- `BEGIN IMMEDIATE` serializes concurrent writers; two concurrent attempts with the same intent can produce at most one committed transition.
- The durable record retains canonical decision, signature, and observation JSON plus their SHA-256 bindings.
- The execution database must be a regular file owned by the service UID and is restricted to mode `0600` after initialization.

## Positive trace

The positive trace remains deliberately boring:

```text
counter = 41
    ↓
Intent(demo.counter.increment)
    ↓
Decision(ALLOW)
    ↓
Ed25519 authority signature
    ↓
public-key verification
    ↓
BEGIN IMMEDIATE
    ↓
check durable replay ledger
    ↓
41 → 42
    ↓
insert durable execution record
    ↓
COMMIT
    ↓
Observation
    ↓
v0.1A evidence receipt + conformance = MATCH
```

## Adversarial acceptance cases

The v0.1B tests cover:

- forged signature under an attacker key;
- decision mutation after signing;
- authority substitution;
- key-ID substitution;
- replay after store/executor re-instantiation;
- injected failure after the counter update but before the execution record insertion;
- duplicate observation-ID collision and rollback;
- two concurrent executions of the same intent;
- executor/verifier API checks showing that neither object exposes a private key or signing method;
- database owner-only permission enforcement;
- rejection of a relative execution-store path.

## Claims boundary

When the v0.1B tests and repository gates pass, the implementation may claim only:

- durable software replay rejection for the bounded SQLite-backed demo action;
- transactional atomicity between the SQLite-resident demo state transition and its SQLite execution record;
- Ed25519 signature verification of canonical software decisions under a configured public key;
- software API separation between decision signing and execution verification;
- persistence of canonical decision/signature/observation evidence sufficient to independently recompute their software hashes.

v0.1B does **not** establish:

- atomicity for external OS commands, filesystems outside the SQLite transaction, network calls, services, containers, robots, vehicles, manufacturing equipment, or physical devices;
- distributed exactly-once semantics or Byzantine fault tolerance;
- HSM, TPM, Secure Boot, measured boot, remote attestation, or non-exportable key custody;
- process isolation between the authority signer and executor;
- key rotation, threshold signatures, quorum authorization, revocation, PKI, certificate lifecycle, or external trust federation;
- production hardening, certification, accreditation, CMMC/NIST compliance, or legal/compliance status;
- authorization for consequential autonomy or live-value operation.

## Promotion rule

A real SARA/PRIME action adapter remains blocked. The next promotion gate must explicitly address the gap between **transactional state stored inside the same database** and **non-transactional external side effects**. Until that is solved with an idempotency/reconciliation design and fault-injection evidence, v0.1B remains a harmless software demonstration boundary.
