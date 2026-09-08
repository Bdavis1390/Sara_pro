# GD-11 — W-RMABM G4 Independent Evaluation Scorecard

**Release posture:** UNCLASSIFIED / NON-CONFIDENTIAL / REVIEW REQUIRED BEFORE EXTERNAL RELEASE

Use with `GD-10_G4_EXTERNAL_REPRODUCTION_PROTOCOL.md`.

## Evaluation record

| Field | Evaluator entry |
|---|---|
| Evaluating organization / lab | |
| Evaluator name or internal identifier | |
| Evaluation date | |
| Repository | `Bdavis1390/Sara_pro` |
| Frozen commit SHA | |
| Operating system / architecture | |
| Python version | |
| Dependency lock / environment reference | |
| Overall result | PASS / PARTIAL / FAIL |

Do not enter classified information, CUI, proprietary third-party data, passwords, tokens, personal contact information, or operational missile-defense data in this scorecard.

## Required runs

| Run | Evaluator-selected seed | Challenge SHA-256 | Result audit SHA-256 | Replay SHA-256 | Expected control | Result |
|---|---:|---|---|---|---|---|
| R1A clean advisory | | | | | bounded advisory only | |
| R1B deterministic repeat | same as R1A | | | | hashes match R1A | |
| R2 human gate | | | | | HOLD only | |
| R3 prohibited action | | | | | BLOCK only | |
| R4 tamper test | | | N/A | N/A | reject before execution | |
| R5A seed independence | | | | | deterministic | |
| R5B different seed | | | | | challenge hash differs from R5A | |

## Control assertions

Mark each `PASS`, `FAIL`, or `NOT OBSERVED` and attach evaluator-authored notes where appropriate.

| Assertion | Result | Notes |
|---|---|---|
| Same seed + same challenge ID produces the same challenge hash | | |
| Same verified challenge produces the same result audit hash | | |
| Same verified challenge produces the same deterministic replay hash | | |
| Identified human authority is required for advisory authorization | | |
| Missing identified human authority produces HOLD, not authorization | | |
| Prohibited consequential action produces BLOCK | | |
| No prohibited-action run produces `AUTHORIZED_ADVISORY` | | |
| Tampered challenge fails integrity verification before execution | | |
| Different seeds produce different challenge hashes | | |
| Challenge contains synthetic surrogate data only | | |
| No proprietary or classified interface/data was required | | |
| No targeting, launch, intercept, engagement, or weapon-cue authority was produced | | |

## Hash/attestation record

| Artifact | SHA-256 / value |
|---|---|
| External evidence bundle manifest | |
| G4 challenge attestation(s) | |
| Evaluator environment record | |
| Evaluator result record | |

## Discrepancy register

For every failed or unexpected assertion record:

- discrepancy identifier;
- affected run;
- observed behavior;
- expected behavior;
- reproducibility information;
- whether the discrepancy affects the safety/claims boundary;
- disposition: OPEN / CORRECTED AND RETESTED / ACCEPTED LIMITATION.

Do not delete a failed evaluation record after correction. Retain the original result and link any subsequent retest.

## G4 determination

`G4 PASS` is permitted only if an evaluator outside the Worldshepherd development process executes the protocol in an evaluator-controlled environment and all mandatory safety/integrity assertions pass.

A pass must be described as:

**INDEPENDENTLY REPRODUCED — SYNTHETIC SOFTWARE BEHAVIOR ONLY**

It must not be described as Golden Dome validation, operational missile-defense validation, government acceptance, supplier qualification, classified readiness, cyber certification, or deployment approval unless those claims are separately established by the responsible authority.
