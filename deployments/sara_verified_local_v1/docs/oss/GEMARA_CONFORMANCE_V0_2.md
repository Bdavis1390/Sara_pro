# Worldshepherd Gemara conformance evidence v0.2

Status: **PINNED UPSTREAM CUE SEMANTIC VALIDATION PASS**

This evidence record covers the full Gemara projections generated from the frozen Worldshepherd interoperability corpus v0.1. It does not modify the frozen source corpus and does not upgrade any OCSF claim.

## Validation basis

- Worldshepherd source branch: `interop/ocsf-gemara-fixtures-v1`
- Source corpus: `fixtures/standards_interop/corpus_v0_1.json`
- Frozen corpus digest: `sha256:702ed3ed00edd77b12a04061bcadba5c62e894787d88db3bcb0b1a6e7b736ac7`
- Gemara schema repository: `gemaraproj/gemara`
- Gemara schema commit: `24e52e93bc71e28507e1942ce543e26ab58a7f25`
- Gemara schema version at that commit: `v0.17.0-dev`
- CUE validator version: `v0.15.1`
- GitHub Actions workflow: `Worldshepherd Gemara Conformance v0.2`
- Passing workflow run: `34795936536`

## Scope

Seven frozen Worldshepherd cases are projected into three complete Gemara document types each:

- `EvaluationLog`
- `EnforcementLog`
- `AuditLog`

Total documents semantically validated: **21**.

Each generated document includes required Gemara metadata and target information. Evaluation records contain control evaluations and assessment logs with pinned source evidence. Enforcement records contain explicit dispositions, methods, steps, and assessment justification. Audit records contain criteria, typed results, evidence, and review recommendations for non-passing cases.

## Result mapping

Worldshepherd operational outcomes are not collapsed into one generic pass/fail state. The projection uses:

- ordinary allowed operations → Gemara `Passed` / enforcement `Clear`;
- policy-denied attempted operation → Gemara `Failed` / enforcement `Enforced`;
- declared-read-only capability observed writing → Gemara `Needs Review` / enforcement `Undetermined`;
- interrupted execution → Gemara `Unknown` / enforcement `Undetermined`.

This distinction keeps system-control correctness separate from the compliance state of the attempted action.

## Validator result

The workflow successfully completed all of the following gates:

1. install the Worldshepherd test package;
2. run the internal Gemara projection and frozen-corpus regression tests;
3. deterministically generate all 21 complete Gemara JSON documents;
4. check out the exact upstream Gemara schema commit;
5. install the pinned CUE validator;
6. run `cue vet` against `#EvaluationLog`, `#EnforcementLog`, and `#AuditLog` for every corresponding generated document.

The authoritative CUE semantic-validation step completed successfully.

## Claims boundary

This result establishes **schema-level semantic conformance of these 21 synthetic Gemara documents against the pinned upstream Gemara CUE schema commit**.

It does **not** establish:

- Gemara certification or endorsement;
- OpenSSF endorsement;
- OCSF conformance;
- partner validation;
- production interoperability;
- government acceptance;
- operational security accreditation;
- correctness outside the frozen synthetic fixture scope.

Any future change to the source corpus, Gemara schema commit, projection logic, or validator version requires a new evidence run. The v0.1 corpus itself remains frozen and versioned rather than silently mutated.
