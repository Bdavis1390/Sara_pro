# Contributing to Worldshepherd / SARA

Contributions are welcome when they improve reproducibility, evidence quality, implementation, documentation, or validation.

## Before opening a pull request

1. Identify the affected capability lane.
2. State the current claim state and the claim state your change actually supports.
3. Separate code changes from research assertions.
4. Add or update tests where software behavior changes.
5. Preserve negative evidence, known limitations, and failed cases.
6. Do not commit secrets, CUI, export-controlled data, proprietary partner material, or private contact information.

## Required PR content

Every substantive PR should answer:

- **Problem:** What bounded problem is being solved?
- **Change:** What changed?
- **Evidence:** What proves the change behaves as stated?
- **Claim state:** Which Worldshepherd claim-state labels apply?
- **Limitations:** What remains unproven or unsupported?
- **Validation:** What commands/tests/review steps were run?
- **Risk:** What could regress, fail, or be misinterpreted?

## Claim-state labels

Use the canonical policy in `docs/CLAIMS_AND_EVIDENCE_POLICY.md`.

Common examples:

- code exists but physical integration is not tested: `IMPLEMENTED IN SOFTWARE` + `REQUIRES PARTNER VALIDATION`;
- model results only: `SIMULATED ONLY`;
- literature-backed research direction: `SUPPORTED BY LITERATURE` + `REQUIRES LAB VALIDATION`;
- proposed mechanism without sufficient evidence: `HYPOTHESIS`;
- certification or partner acceptance not yet obtained: explicitly say so.

## Software contributions

For software changes:

- keep interfaces explicit;
- fail closed on authorization/validation errors;
- add tests for permission boundaries and negative cases when relevant;
- keep logs useful without exposing secrets;
- prefer deterministic fixtures for evidence-producing tests;
- document supported runtime/tool versions;
- include rollback/migration notes for stateful changes.

## Research contributions

For physical-science or engineering research:

- state assumptions and governing equations;
- cite the source basis where applicable;
- distinguish prior art from Worldshepherd work;
- include uncertainty/sensitivity analysis for numerical claims;
- predeclare measurable validation gates;
- do not convert a simulation into a hardware-performance claim.

## Commit style

Prefer bounded, descriptive commits, for example:

```text
Add PRE schema validation for missing source status
Document APNT partner-validation boundary
Test rollback evidence manifest generation
```

Avoid vague commit messages such as `update`, `stuff`, or `final`.

## Definition of done

A contribution is complete when another competent reviewer can determine:

1. what changed;
2. why it changed;
3. what evidence supports it;
4. what is still not established;
5. how to reproduce or independently evaluate the result.
