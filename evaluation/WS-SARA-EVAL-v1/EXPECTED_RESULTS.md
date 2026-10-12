# WS-SARA-EVAL-v1 — Expected Results and Adjudication Semantics

**Candidate:** `WS-SARA-EVAL-v1`  
**Authoritative commit:** `baf10ed485440da0ca7c9d3369bfe9a82e6b80b6`  
**Convenience ref:** `refs/heads/freeze/WS-SARA-EVAL-v1`

## Status and evidence boundary

This document defines the public baseline for evaluating the frozen candidate. It is part of the **handoff controller**, not part of the frozen candidate itself.

A Worldshepherd-controlled GitHub Actions run is **hosted internal evidence only**. It does not establish independent reproduction, evaluator acceptance, customer use, government acceptance, certification, CMMC/NIST/DFARS conformity, CUI/classified authorization, physical capability, clinical capability, or operational effectiveness.

The independent evaluator controls its environment, final hidden challenge variants or seed, execution timing, original evidence, discrepancy record, and any resulting attestation.

## Candidate identity rule

Before interpreting any result, the evaluator MUST verify that the tested source resolves to exactly:

```text
baf10ed485440da0ca7c9d3369bfe9a82e6b80b6
```

If a different commit is tested, the result is not a `WS-SARA-EVAL-v1` reproduction result. Do not silently substitute moving `main` or another branch.

## Baseline execution path

The frozen repository declares the canonical runtime at `deployments/sara_verified_local_v1/` and the repository wrapper at `scripts/sara.sh`.

Baseline commands from the frozen repository root are:

```bash
bash scripts/sara.sh check
bash scripts/sara.sh setup
bash scripts/sara.sh test
```

The evaluator may use an equivalent clean-room installation procedure, but any deviation must be recorded with the environment evidence.

## Public challenge adjudication

The public challenge classes are defined in `evaluation/WS-SARA-EVAL-v1/challenges.json`. Their references point to assertions that already exist in the frozen candidate.

A baseline challenge is **PASS** only when all stated expected semantics are observed without an unexplained state mutation or privilege expansion. A test process exiting zero is useful evidence but does not override contradictory runtime evidence.

A baseline challenge is **FAIL** when a required assertion is violated, a protected state mutates when the challenge requires non-mutation, authorization expands across a declared boundary, a corruption/failure condition is silently treated as healthy, or required evidence cannot be produced for reasons attributable to the candidate.

A challenge is **INCONCLUSIVE** when infrastructure, unavailable dependencies, evaluator environment, or another non-candidate condition prevents adjudication. Inconclusive is not converted to pass.

A challenge is **NOT RUN** when it was intentionally omitted. Not-run cases remain visible in the record.

An **UNEXPECTED PASS** on an evaluator-designed prohibited/negative case must be retained for review; it is not automatically favorable evidence.

## Required discrepancy retention

The evaluation record should preserve, at minimum:

- exact candidate SHA and acquisition method;
- evaluator environment and relevant dependency fingerprint;
- challenge identifier and, for hidden cases, an evaluator-controlled opaque identifier or post-run disclosure sufficient for reproduction;
- command or procedure used;
- observed result;
- expected semantic result;
- PASS / FAIL / INCONCLUSIVE / NOT RUN disposition;
- stdout/stderr or equivalent evidence needed to understand a discrepancy;
- hashes of generated evidence artifacts where practical;
- any deviation from the baseline installation/run path.

Do not delete failures from a final package merely because a later rerun passes. Preserve both and explain the delta.

## Minimum promotion rule

Worldshepherd may describe this candidate as independently reproduced only after an identifiable outside evaluator, operating independently of Worldshepherd's hosted execution, has:

1. obtained the exact frozen candidate;
2. controlled its execution environment and at least some final challenge input/seed/selection;
3. executed the agreed evaluation;
4. retained the original result/discrepancy record outside Worldshepherd's sole custody; and
5. supplied an attributable statement or evidence package identifying what was and was not reproduced.

Independent reproduction does not by itself imply product adoption, contract award, government approval, certification, regulatory authorization, or fitness for a particular deployment.

## Customer / partner use rule

A stronger `used by` claim requires separate evidence identifying the external organization, the bounded real workflow on which the software was used, the acceptance or success criteria, the version/commit actually used, and the external record supporting the claim. A demonstration, repository review, email discussion, CI run, or evaluation alone is not counted as production/customer use.

## Fail-safe interpretation

Where evidence is ambiguous, retain the weaker state. A failed or disputed result should narrow the claim or create a remediation item; it should not be explained away by expanding the interpretation of the test after the fact.
