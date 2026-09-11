# WS-SARA-EVAL-v1 — Evidence Manifest Template

This template is completed by the evaluator for the received bundle and produced evidence. Do not pre-populate hashes that have not been independently computed in the evaluator environment.

## Identity

- source baseline SHA: `1c7be6c51ffd475f124e951f6c8c76208460b895`
- evaluator documentation bundle commit: `<record exact commit received>`
- evaluator organization/reference: `<value>`
- evaluation date: `<value>`

## Received bundle

| Artifact/path | SHA-256 | Notes |
|---|---|---|
| source archive / checkout record | | |
| evaluator protocol | | |
| evaluator scorecard | | |
| release note | | |
| installation/deployment instructions used | | |
| dependency/environment lock used | | |

## Produced evidence

| Run | Artifact/path | SHA-256 | Result |
|---|---|---|---|
| C1 | | | PASS / FAIL |
| C2 | | | PASS / FAIL |
| C3 | | | PASS / FAIL |
| C4 | | | PASS / FAIL |
| C5 | | | PASS / FAIL |
| C6 | | | PASS / FAIL |

## Discrepancy preservation

Every failed or unexpected run receives a unique discrepancy ID and an independently retained original artifact. A corrected retest must be stored as a new record and linked to the failure; the original failure must not be deleted or replaced.

## Attestation boundary

Completing this manifest does not by itself establish independence. Independence requires that the evaluator actually be outside the Worldshepherd development process and control its own execution environment and original evidence record.
