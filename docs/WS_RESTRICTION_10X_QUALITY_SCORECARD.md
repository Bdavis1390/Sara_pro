# WS-RESTRICTION 10X QUALITY SCORECARD

Status: **ENGINEERING ACCEPTANCE STANDARD / G7 INTERNAL VALIDATION PENDING**

## Definition of "10x better"

For this restriction-evidence lane, "better" is measured as **operator assurance ambiguity**, not a subjective quality rating.

The frozen baseline is ten assurance questions that an operator should not have to infer manually when deciding whether a restriction record is trustworthy:

1. Is the restriction semantic identity valid?
2. Is the SARA event identity bound to that restriction?
3. Are the delivery semantics explicit and valid?
4. Is the governing authority PRIME SENTINEL?
5. Is that authority bound inside the evidence identity?
6. Is the non-secret fingerprint-key epoch identified?
7. Was the record cryptographically verified?
8. Is the PRIME signing key identified?
9. Is the configured signing public-key fingerprint known?
10. Is raw-content persistence explicitly false?

Each unresolved question is one manual-inference unit.

Baseline manual-inference units: **10**.

10x acceptance threshold: **<=1 unresolved unit**.

The stronger practical V4 acceptance condition is **0/10 unresolved**.

## Executable implementation

`restriction_assurance_dimensions()` derives the ten facts from the already validated non-content projection.

It does not inspect or return raw restricted content, safe summaries, arbitrary metadata, or signature bytes.

`restriction_observability()` reports:

```json
{
  "assurance_quality": {
    "required_dimensions_per_record": 10,
    "fully_resolved_v4_records": 1,
    "unresolved_dimensions": 0
  }
}
```

The required G7 test proves a valid V4 record resolves 10/10 dimensions with zero unresolved.

A V2 historical control remains readable but cannot claim the fully resolved V4 state.

## What this metric does not mean

It does not mean Worldshepherd is globally "10x better" in every performance or mission dimension.

It means the selected operator-assurance ambiguity metric improves by at least one order of magnitude against the frozen baseline.

Other engineering dimensions such as latency, throughput, recovery time, availability, model quality, and physical-system performance require their own baselines and measurements.

## Non-regression

A V4 record cannot receive full-quality status unless the underlying validators have already accepted:

- semantic restriction ID;
- event ID;
- PRIME authority;
- authority payload binding;
- fingerprint-key epoch;
- live Ed25519 verification;
- signing key ID;
- configured public-key fingerprint;
- raw-content-persistence assertion;
- at-least-once delivery semantics.

Any failed dimension prevents `fully_resolved_v4_records` from incrementing.

## Claims state

Until G7 passes exact-head required CI, the broader Verified Local deployment/recovery/evidence gate, and protected merge, classify this scorecard implementation as **IMPLEMENTED IN SOFTWARE / PENDING INTERNAL VALIDATION**.
