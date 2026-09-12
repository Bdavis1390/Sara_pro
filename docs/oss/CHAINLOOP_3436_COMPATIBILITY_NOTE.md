# Chainloop #3436 compatibility note for fan-out resiliency

Upstream inputs:

- `chainloop-dev/chainloop#39` — durable/resilient integration fan-out problem
- merged `chainloop-dev/chainloop#3436` — adjudication outcome fields in `ai-security-context-0.1`

Claims state: **DESIGN ALIGNMENT / NOT UPSTREAM ACCEPTED**

## Upstream change

PR #3436 adds optional fields that describe adjudication outcomes:

- `unresolved[].retryable`
- `survivors[].verdict`
- `survivors[].verdict_reason`
- `stats.abandoned`

These fields belong to the source evidence/adjudication model. A durable fan-out system should preserve them when present instead of creating competing outcome semantics.

## Required separation

Two independent questions must remain visible:

1. **Evidence/adjudication outcome** — what the source artifact says about the commit or item.
2. **Delivery outcome** — whether the integration fan-out successfully delivered that artifact.

For example, a source item can have `retryable=false` while a network delivery is still retried because the target was temporarily unavailable. Retrying transport must not re-adjudicate or rewrite the source evidence.

## Recommended durable receipt projection

A delivery receipt may expose a bounded projection for operations/search while retaining the source digest as authority:

```text
source_schema                  ai-security-context-0.1
source_digest                  sha256:...
adjudication.retryable         bool/null
adjudication.verdict           string/null
adjudication.verdict_reason    string/null
adjudication.abandoned_count   integer/null
```

Rules:

- the signed/content-addressed source artifact remains authoritative;
- projected values must exactly match the source identified by `source_digest`;
- transport retry/dead-letter state never rewrites source verdict fields;
- replay of a delivery never mutates the original adjudication record;
- free-form verdict reasons should not be metric labels.

## Additional test invariants

Add these to the #39 proposal validation set:

1. **Semantic separation:** source retryability and delivery retryability remain independently queryable.
2. **Projection fidelity:** receipt projection equals the source artifact for the same digest.
3. **Replay immutability:** re-delivery does not modify adjudication fields.
4. **Backward compatibility:** artifacts without the new optional fields continue through the fan-out path unchanged.

This note supplements `CHAINLOOP_FANOUT_RESILIENCY_PROPOSAL.md`; it does not claim that #3436 implements delivery resiliency or that #39 has accepted this design.
