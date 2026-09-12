# Chainloop fan-out resiliency proposal

Upstream target: `chainloop-dev/chainloop#39`

## Problem

Integration fan-out that is launched from an in-process goroutine has no durable delivery guarantee. A process restart can lose work, operators lack an authoritative receipt, and historical attestations cannot be replayed cleanly.

The objective should be **durable at-least-once dispatch with deterministic idempotency and an auditable delivery ledger**. The queue/broker is transport; it should not become the sole source of truth.

## Proposed architecture

### 1. Persist fan-out intent

When an attestation reaches the state at which integrations should fire, create an outbox record in the same logical commit boundary.

Suggested fields:

```text
id                    UUID
idempotency_key       string UNIQUE
attestation_id        UUID
integration_id        UUID
event_kind            string
payload_digest        string
payload_ref           string/null
state                 enum
attempt_count         integer
next_attempt_at       timestamp/null
last_attempt_at       timestamp/null
acked_at               timestamp/null
last_error_class      string/null
last_error_message    string/null
replay_of             UUID/null
requested_by          string/null
request_reason        string/null
created_at            timestamp
updated_at            timestamp
```

Recommended deterministic idempotency key:

```text
sha256(attestation_id || integration_id || event_kind || payload_digest)
```

Retries use the same key. An explicit replay can either reuse the original key when the intended semantic is retry, or create a new delivery identity with `replay_of=<original id>` when the operator is intentionally reissuing the event.

### 2. Explicit state machine

```text
PENDING
  -> DISPATCHED
      -> ACKED
      -> RETRY_WAIT
      -> DEAD_LETTER
  -> CANCELLED

RETRY_WAIT
  -> DISPATCHED
  -> DEAD_LETTER

DEAD_LETTER
  -> PENDING      (operator-approved replay/requeue)
```

State transitions should be compare-and-set/transactional so two workers cannot own the same delivery simultaneously without a lease expiring.

### 3. Queue transport

JetStream is a reasonable transport for the issue, but delivery correctness should not depend on JetStream retaining history indefinitely.

Recommended flow:

```text
Attestation commit
      |
      v
Persistent outbox
      |
      v
Publisher -> JetStream subject
      |
      v
Worker -> integration adapter
      |
      +--> durable target success -> ACKED
      +--> retryable error        -> RETRY_WAIT
      +--> terminal error         -> DEAD_LETTER
```

The worker should acknowledge the broker message only after the outbox transition is durable.

### 4. Error taxonomy

Adapters should normalize errors into a small transport-independent taxonomy:

```text
AUTHENTICATION_FAILED   terminal until configuration changes
AUTHORIZATION_FAILED    terminal until configuration changes
PAYLOAD_INVALID         terminal
TARGET_NOT_FOUND        policy-dependent
RATE_LIMITED            retryable; honor Retry-After when present
TARGET_UNAVAILABLE      retryable
TIMEOUT                 retryable
CONNECTION_ERROR        retryable
CONFLICT                adapter-specific; may represent idempotent success
UNKNOWN                 retry with bounded policy, then dead-letter
```

This prevents every integration from inventing its own retry semantics.

### 5. Replay semantics

Replay should be an API/operator capability rather than an undocumented queue operation.

A replay request should record:

- original delivery ID;
- requesting principal;
- reason;
- request timestamp;
- whether the replay preserves or creates a new idempotency identity.

The original attestation remains immutable.

### 6. Observability

Recommended metrics:

```text
chainloop.integration.delivery.pending
chainloop.integration.delivery.acked
chainloop.integration.delivery.retry
chainloop.integration.delivery.dead_letter
chainloop.integration.delivery.age
chainloop.integration.delivery.attempts
chainloop.integration.delivery.latency
```

Dimensions should stay bounded: integration type/name, result class, event kind. Avoid attestation IDs as metric labels.

## Safety properties / testable invariants

1. **No lost intent after commit:** once the attestation and outbox record are committed, killing the process at any later instruction boundary cannot erase the intended fan-out.
2. **Retry stability:** retrying a delivery does not change its deterministic idempotency key.
3. **Crash-after-effect safety:** if the target side effect succeeds and the worker crashes before local ACK, the retry is safe at an idempotent receiver.
4. **Audit completeness:** every terminal state can be explained from persisted state without depending on ephemeral logs.
5. **Replay immutability:** replay never modifies the original attestation or original delivery record.
6. **Bounded failure:** a permanently failing integration cannot create an infinite hot retry loop.
7. **Worker concurrency:** two workers cannot simultaneously advance the same delivery unless a lease expires and takeover is explicit.

## Suggested implementation sequence

### Phase A — semantics first

- outbox model and migration;
- state transitions;
- replay/requeue API;
- adapter error taxonomy;
- unit/property tests around crash boundaries and idempotency.

### Phase B — broker execution

- JetStream publisher;
- consumer workers;
- leases/visibility timeout;
- retry scheduling and dead-letter policy;
- operational metrics.

Separating the two phases makes the delivery contract independently testable from the message-broker choice.

## Compatibility

Existing integrations can initially be wrapped as adapters behind the new dispatcher. The public attestation contract need not change. A feature flag can permit gradual rollout while old goroutine dispatch remains available during migration.
