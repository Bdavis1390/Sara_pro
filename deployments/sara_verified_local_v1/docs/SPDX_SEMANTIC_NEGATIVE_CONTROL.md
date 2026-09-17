# SPDX 3.0.1 Semantic Negative Control

## Purpose

This follow-on test asks a stricter question than validator agreement:

> Can the Worldshepherd validation harness demonstrate a document that is structurally valid under the canonical SPDX 3.0.1 JSON Schema but semantically invalid under the canonical SPDX 3.0.1 SHACL model?

The work is isolated from the already validated SPDX intake and validator-triangulation branches so those review surfaces remain stable.

## Canonical rule used

SPDX 3.0.1 defines `Core/createdBy` as an object property whose range is `Core/Agent`:

- https://spdx.github.io/spdx-spec/v3.0.1/model/Core/Properties/createdBy/
- https://spdx.github.io/spdx-spec/v3.0.1/model/Core/Classes/CreationInfo/

The baseline fixture contains a `CreationInfo` object whose `createdBy` points to a `Person`, which is an `Agent` subclass.

The negative control changes only that reference so `CreationInfo.createdBy` points to the existing `software_Package` instead.

No new field is introduced and the reference remains a syntactically valid SPDX identifier. The intended distinction is therefore:

1. the canonical JSON Schema accepts the document because its serialized structure remains valid; and
2. the canonical SHACL model rejects the document because the referenced object is not an `Agent`.

## Required observations

The gate may claim success only if all of the following occur in one run against the same mutation:

- the unmodified baseline passes AJV;
- the unmodified baseline passes direct pySHACL;
- the unmodified baseline passes `spdx3-validate`;
- the mutated document still passes AJV structural validation;
- direct pySHACL rejects the mutated document as non-conformant; and
- `spdx3-validate` also rejects the mutated document.

If AJV rejects the mutation, the control is not semantic-only and the gate fails.

If pySHACL accepts it, semantic discrimination was not demonstrated and the gate fails.

Tool/runtime failures are not counted as semantic rejection.

## Provenance improvement

Pull-request workflows normally check out GitHub's synthetic merge commit. Therefore the evidence record stores two distinct identities:

- `pull_request_head_sha` — the exact source branch head under review; and
- `workflow_checkout_sha` — the synthetic merge commit actually executed by the workflow.

This avoids treating a merge-ref SHA as if it were the branch-head identity.

## Evidence state

The maximum positive state for this gate is:

`SCHEMA_VALID_SEMANTIC_INVALID_CONTROL_PROVEN`

This means only that one exact wrong-range reference is accepted structurally and rejected semantically by the pinned SPDX 3.0.1 resources and validator versions.

## Hard claims boundary

Even after a passing run:

```text
semantic_engine_diversity_established = false
general_spdx_conformance_established = false
arbitrary_input_conformance_established = false
independent_external_validation_established = false
community_endorsement_established = false
admission_authorized = false
release_approved = false
```

The semantic validators still share pySHACL lineage, so this test establishes **structural-versus-semantic discrimination**, not independent semantic-engine diversity.

## Claims state

`IMPLEMENTED IN SOFTWARE / SEMANTIC NEGATIVE CONTROL CI PENDING`
