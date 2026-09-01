# WS Intake Minimum Standard PR Notes — 2026-09-01

## What this increment proves

This increment proves that Worldshepherd/SARA has an enforced intake-minimum validator in code and tests. New intakes can now be checked for the minimum fields required before they are used to move PRE, opportunity, partner, security, release, or standards posture.

## What this increment does not prove

This increment does not prove that every future external intake has already been processed through the standard. It creates the gate and fixture. The next pull request should wire the gate into the SARA Verified Local v1 workflow and add release-index custody for the resulting artifact.

## Safe operating interpretation

Until workflow integration lands, use this as the standing source-of-truth rule:

```text
No new intake should be promoted unless it has:
  - source custody
  - source digest
  - evidence status
  - maturity label
  - human-review status
  - routing status
  - downstream route or evidence
  - explicit non-claim boundary
```

Any intake missing those fields remains `RAW_INTAKE` or `PENDING_ROUTE`; it must not raise maturity, probability, compliance, partner, remediation, or operational-authority posture.
