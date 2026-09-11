# WS-SARA-EVAL-v1 — Independent Evaluation Scorecard

Use with `WS-SARA-EVAL-v1_SCOPE_AND_PROTOCOL.md`.

**Source-code baseline:** `1c7be6c51ffd475f124e951f6c8c76208460b895`

## Evaluation record

| Field | Evaluator entry |
|---|---|
| Evaluating organization / lab | |
| Evaluator name or controlled identifier | |
| Evaluation date | |
| Source repository | `Bdavis1390/Sara_pro` |
| Frozen source baseline SHA | `1c7be6c51ffd475f124e951f6c8c76208460b895` |
| Received bundle SHA-256 | |
| Operating system / architecture | |
| Python/runtime version | |
| Docker / Compose version if used | |
| Dependency / environment fingerprint | |
| Network boundary | |
| Overall result | PASS / PARTIAL / FAIL |

Do not place passwords, tokens, private keys, CUI, classified data, export-controlled third-party data, or proprietary customer information in this scorecard.

## Required runs

| Run | Expected control | Result | Evidence / hash | Notes |
|---|---|---|---|---|
| C1 clean deployment + health/readiness | reviewed local baseline reproduces | | | |
| C2 authorization separation | unauthorized/admin boundary fails closed | | | |
| C3 registry + audit traceability | authorized bounded change is traceable | | | |
| C4 PRIME issuance durability/idempotency | frozen v1.5 documented behavior reproduces | | | |
| C5 malformed/unauthorized cases | no silent promotion to success | | | |
| C6 restart/recovery | documented persisted/recovery behavior reproduces | | | |

## Control assertions

Mark each `PASS`, `FAIL`, or `NOT OBSERVED`.

| Assertion | Result | Notes |
|---|---|---|
| Exact frozen source identity was used | | |
| Evaluator controlled the execution environment | | |
| Localhost/network boundary matched reviewed instructions | | |
| Administrative and operator authority remained separated | | |
| Unauthorized administrative operation did not silently succeed | | |
| Bounded authorized registry operation was traceable | | |
| Relevant audit/evidence output was retained | | |
| PRIME same-request retry behavior matched frozen v1.5 contract | | |
| PRIME conflicting request reuse was rejected as documented | | |
| Relevant restart persistence behavior matched frozen v1.5 scope | | |
| Malformed/unauthorized input was not silently accepted | | |
| Failed runs, if any, were retained | | |
| Retests, if any, were recorded as new linked evidence | | |
| No unmerged ECHO v1.6 behavior was attributed to this baseline | | |
| No W-RMABM behavior was attributed to this core baseline unless separately evaluated | | |
| No physical, certification, government/customer acceptance, or classified-readiness claim was inferred | | |

## Evidence inventory

| Artifact | SHA-256 / value | Custodian |
|---|---|---|
| Received evaluator bundle | | |
| Environment record | | |
| C1 evidence | | |
| C2 evidence | | |
| C3 evidence | | |
| C4 evidence | | |
| C5 evidence | | |
| C6 evidence | | |
| Evaluator result record | | |

## Discrepancy register

For each discrepancy retain:

- discrepancy ID;
- affected run;
- observed behavior;
- expected behavior;
- reproducibility information;
- safety/claims impact;
- disposition: `OPEN`, `CORRECTED_AND_RETESTED`, or `ACCEPTED_LIMITATION`;
- link/reference to the original evidence;
- link/reference to any later retest.

Do not delete or overwrite a failed evaluation record after correction.

## Determination

A successful result may be described only as:

**INDEPENDENTLY REPRODUCED — BOUNDED SOFTWARE BEHAVIOR ONLY**

unless broader evidence has been separately established and reviewed.
