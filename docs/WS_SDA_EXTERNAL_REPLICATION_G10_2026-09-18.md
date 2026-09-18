# WS-SDA G10 — Independent Replication Package

Status: **VALIDATOR + HANDOFF PACKAGE IMPLEMENTED — EXTERNAL REPLICATION NOT YET RECEIVED**
Date: 2026-09-18
Branch: `feature/ws-sda-g10-independent-replication-20260918`
Parent stack: G1 -> G9

## 1. Objective

G10 is intentionally outside the Worldshepherd-controlled evidence boundary.

Internal CI can build the handoff package and verify the replication-assertion
format, but it cannot independently validate itself.

The G10 gate therefore requires an evaluator outside the Worldshepherd-controlled
execution environment to run the frozen materials and return independently
attributable evidence.

## 2. Frozen inputs

The replication package binds:

- exact candidate source commit;
- exact G8 corpus SHA-256;
- exact G9 protocol SHA-256;
- baseline measurement bundle SHA-256;
- candidate measurement bundle SHA-256;
- G9 report SHA-256;
- evaluator-controlled challenge reference;
- external environment evidence SHA-256;
- raw evidence SHA-256.

No result may silently substitute a different source commit or benchmark workload.

## 3. Evaluator-signed assertion

`sda_external_replication.py` defines a signed Ed25519 assertion containing:

- evaluator name and organization;
- separate evaluator-identity evidence reference;
- evaluator key ID and public-key fingerprint;
- exact artifact digests;
- exact source commit;
- evaluator-controlled challenge reference;
- environment ID;
- explicit declaration whether execution was Worldshepherd-controlled;
- start/completion timestamps;
- PASS / FAIL / DISCREPANCY result;
- whether the evaluator independently reproduced G9 eligibility;
- unresolved discrepancies;
- raw evidence references.

The signature proves possession of the supplied evaluator key. It does **not** by
itself prove the evaluator's legal/institutional identity or independence.

## 4. Gate conditions

G10 passes only when all are true:

```text
external signature valid
AND public-key fingerprint matches signed assertion
AND exact candidate commit matches
AND exact G8 corpus matches
AND exact G9 protocol matches
AND execution is not Worldshepherd-controlled
AND evaluator identity has been separately verified
AND external result == PASS
AND external evaluator reproduced G9 eligibility
AND unresolved discrepancy count == 0
```

A cryptographically valid self-run cannot pass the independent gate.

A different source commit or benchmark digest cannot pass.

A PASS label with unresolved discrepancies is structurally rejected.

## 5. Failure evidence is preserved

An evaluator FAIL or DISCREPANCY assertion is still useful evidence.

The verifier records it as a cryptographically attributable result but leaves:

```text
g10_independent_replication_gate_passed = false
```

Negative results must not be discarded or rewritten into a pass.

## 6. Claims boundary

A future G10 gate pass establishes independent reproduction only for the exact
frozen WS-SDA candidate, G8 workload, G9 protocol, external environment and evidence
package.

It does not establish:

- universal or permanent 10x security;
- completeness against every adversary;
- operational orbit/track accuracy;
- targeting, weapon cueing, or actuation authorization;
- classified-network approval;
- CMMC, NIST, FIPS, SLSA, RMF/ATO or other certification/conformity;
- government procurement selection;
- customer deployment.

Those remain separate evidence gates.

## 7. Current state

Current G10 state:

```text
VALIDATOR_IMPLEMENTED
HANDOFF_PACKAGE_IMPLEMENTED
AWAITING_COMPARABLE_REAL_G9_MEASUREMENTS
AWAITING_EXTERNAL_EVALUATOR_EXECUTION
AWAITING_SIGNED_EXTERNAL_ASSERTION
```

No external replication result is claimed.
