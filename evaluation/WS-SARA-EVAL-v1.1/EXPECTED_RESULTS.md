# WS-SARA-EVAL-v1.1 — Expected Results and Adjudication Semantics

**Candidate:** `WS-SARA-EVAL-v1.1`
**Authoritative commit:** `45494ddd32f96b36cef8df37dea33ab405cd4573`
**Convenience ref:** `refs/heads/freeze/WS-SARA-EVAL-v1.1`

## Status and evidence boundary

This document defines the public baseline for evaluating the frozen candidate. It is part of the handoff controller, not part of the frozen candidate itself.

`WS-SARA-EVAL-v1.1` is a successor candidate created after the v1 hosted preflight exposed a clean-environment interpreter-selection defect in the partner-screening verifier. The v1 failure record remains evidence and is not overwritten by v1.1.

A Worldshepherd-controlled GitHub Actions run is **hosted internal evidence only**. It does not establish independent reproduction, evaluator acceptance, customer use, government acceptance, certification, CMMC/NIST/DFARS conformity, CUI/classified authorization, physical capability, clinical capability, or operational effectiveness.

The independent evaluator controls its environment, final hidden challenge variants or seed, execution timing, original evidence, discrepancy record, and any resulting attestation.

## Candidate identity rule

Before interpreting any result, the evaluator MUST verify that the tested source resolves exactly to:

```text
45494ddd32f96b36cef8df37dea33ab405cd4573
```

If a different commit is tested, the result is not a `WS-SARA-EVAL-v1.1` reproduction result. Moving `main` is never substituted silently.

## Baseline execution path

From the frozen repository root:

```bash
bash scripts/sara.sh check
PYTHON=python3 bash scripts/sara.sh setup
bash scripts/sara.sh test
```

Equivalent clean-room procedures are allowed only when the evaluator records the deviation and environment evidence.

## Adjudication

A challenge is **PASS** only when every stated expected semantic is observed and no unexplained state mutation, privilege expansion, or evidence loss occurs.

A challenge is **FAIL** when a required assertion is violated, protected state mutates during a rejection case, authorization expands across a declared boundary, corruption is silently treated as healthy, the portability regression reappears, or required evidence cannot be produced for a reason attributable to the candidate.

A challenge is **INCONCLUSIVE** when infrastructure, unavailable external dependencies, or another non-candidate condition prevents adjudication. Inconclusive is not converted to pass.

A challenge is **NOT RUN** when intentionally omitted and remains visible in the final record.

An **UNEXPECTED PASS** on an evaluator-designed prohibited/negative case must be retained for review; it is not automatically favorable evidence.

## v1 regression closure requirement

`PORTABILITY-01` is mandatory. The v1.1 candidate must demonstrate that the partner-screening verifier resolves the canonical project virtual-environment interpreter when the console entry point is absent from `PATH`, without leaking to an ambient Python lacking declared dependencies.

A v1.1 hosted-preflight pass does not delete or downgrade the v1 discrepancy. It establishes only that the successor candidate did not reproduce that defect under the recorded hosted environment.

## Required discrepancy retention

Retain at minimum:

- exact candidate SHA and acquisition method;
- environment and dependency fingerprint;
- challenge identifier and evaluator-controlled hidden-case identifier where applicable;
- command/procedure used;
- observed and expected result;
- PASS / FAIL / INCONCLUSIVE / NOT RUN disposition;
- stdout/stderr or equivalent discrepancy evidence;
- hashes of generated evidence artifacts where practical;
- deviations from baseline installation/run instructions;
- both failed and corrected runs when remediation occurs.

## Independent reproduction promotion rule

Worldshepherd may describe this candidate as independently reproduced only after an identifiable evaluator outside the Worldshepherd development process has:

1. obtained the exact frozen commit;
2. controlled its execution environment and at least some final challenge input/seed/selection;
3. executed the agreed protocol;
4. retained the original result/discrepancy record outside Worldshepherd's sole custody; and
5. supplied attributable evidence identifying what was and was not reproduced.

Independent reproduction does not imply product adoption, customer use, contract award, government approval, certification, regulatory authorization, or operational effectiveness.

## Customer/partner use rule

A `used by` claim requires separate evidence naming the organization, bounded real workflow, acceptance criteria, exact version/commit, and attributable external record. Review, discussion, CI, demos, or synthetic evaluation alone do not count as customer use.

## Fail-safe interpretation

Where evidence is ambiguous, retain the weaker state. A failure narrows the claim or creates remediation work; test interpretation is not expanded after the fact to manufacture a pass.
