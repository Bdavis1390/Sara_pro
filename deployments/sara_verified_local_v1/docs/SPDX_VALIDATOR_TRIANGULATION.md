# SPDX 3.0.1 Validator Triangulation

## Purpose

This follow-on test asks a narrower question than general SPDX conformance:

> Do multiple validation paths agree on the exact same frozen SPDX 3.0.1 fixture, and do independent structural validators reject a known structural mutation?

The work is intentionally separated from the already validated `worldshepherd-spdx-intake-v1` branch so the primary SPDX community-review surface can remain stable.

## Validation paths

The gate executes three tool paths against the same frozen fixture:

1. `spdx3-validate==0.0.7` — combined SPDX-oriented JSON Schema + SHACL validation;
2. `ajv-cli@5.0.0` — a separate Node.js JSON Schema structural validator; and
3. `pyshacl==0.40.1` — direct SHACL semantic validation.

The versioned canonical SPDX 3.0.1 resources are fetched at run time from:

- `https://spdx.org/schema/3.0.1/spdx-json-schema.json`
- `https://spdx.org/rdf/3.0.1/spdx-model.ttl`

Their SHA-256 digests are captured into the CI evidence record so the exact resources used by a run are attributable.

## Important independence limitation

These are **not three fully independent validation engines**.

`spdx3-validate` itself depends on JSON Schema tooling and pySHACL. Therefore:

- AJV provides a genuinely distinct **structural** validation engine from the Python path used by `spdx3-validate`;
- direct pySHACL execution exercises the canonical model separately but does **not** establish semantic-engine diversity because `spdx3-validate` also depends on pySHACL.

The machine-readable evidence therefore hard-codes:

```text
structural_engine_diversity_established = true
semantic_engine_diversity_established = false
```

## Positive control

The frozen fixture inherited from the SPDX intake branch must pass:

- `spdx3-validate` combined validation;
- AJV structural validation against the versioned SPDX 3.0.1 JSON Schema; and
- direct pySHACL semantic validation against the versioned SPDX 3.0.1 ontology/SHACL model.

Agreement permits only:

`EXACT_FIXTURE_CROSS_VALIDATOR_AGREEMENT`

## Negative structural control

The gate creates an ephemeral mutation of the same fixture by replacing the `SpdxDocument.profileConformance` array with a scalar string.

Both AJV and `spdx3-validate` must reject that mutation. If either validator accepts it, the gate fails.

The mutation is never committed as an authoritative SPDX document; it exists only inside CI as a negative control.

## Evidence record

The uploaded `validator-triangulation.json` binds:

- repository and exact commit SHA;
- fixture path and SHA-256 digest;
- canonical schema/model URLs and the exact fetched resource digests;
- pinned validator names and versions;
- pass/fail results;
- negative-control result; and
- claims boundaries.

## Claims boundary

Even if every validator agrees, the record hard-codes:

```text
general_spdx_conformance_established = false
arbitrary_input_conformance_established = false
independent_external_validation_established = false
community_endorsement_established = false
admission_authorized = false
release_approved = false
legal_license_conclusions_established = false
```

This gate does not claim:

- Worldshepherd is an SPDX-conformant product;
- every future SPDX document will be handled correctly;
- the SPDX community reviewed or endorsed the implementation;
- a human independent reviewer reproduced the result;
- SPDX content is complete, trustworthy, legally sufficient, vulnerability-free, or approved for admission/release.

## Why this is useful for community review

If the three paths agree, the Implementers discussion can focus on the architecture boundary rather than basic fixture syntax. If they disagree, the disagreement itself is the higher-value finding and should block any stronger claim.

The intended community question becomes:

> Is this combination of canonical 3.0.1 resources and validator paths an appropriate downstream interoperability test, and what additional validator or model-level checks would the SPDX community consider authoritative?

## Claims state

`IMPLEMENTED IN SOFTWARE / CROSS-VALIDATOR CI PENDING`
