# Worldshepherd SPDX 3.0.1 Intake Review

## Purpose

This review surface tests how Worldshepherd can consume an SPDX 3.0.1 JSON-LD document as authoritative source evidence without rewriting it or self-declaring SPDX conformance.

The existing `ws-sbom-evidence` path remains unchanged and continues to generate internal CycloneDX 1.5 evidence from the pinned CI dependency freeze. This SPDX work is a separate intake boundary intended for interoperability review with the SPDX community.

## Standards baseline

The adapter is scoped to the SPDX 3.0.1 JSON-LD context:

`https://spdx.org/rdf/3.0.1/spdx-context.jsonld`

Relevant official specification surfaces:

- SPDX 3.0.1 model and serialization: https://spdx.github.io/spdx-spec/v3.0.1/serializations/
- `SpdxDocument`: https://spdx.github.io/spdx-spec/v3.0.1/model/Core/Classes/SpdxDocument/
- software `Sbom`: https://spdx.github.io/spdx-spec/v3.0.1/model/Software/Classes/Sbom/
- software `Package`: https://spdx.github.io/spdx-spec/v3.0.1/model/Software/Classes/Package/
- published examples: https://github.com/spdx/spdx-examples
- validation guidance: https://github.com/spdx/spdx-3-model/blob/develop/serialization/jsonld/validation.md

The SPDX specification states that JSON-LD conformance requires both structural validation against the SPDX JSON Schema and semantic validation against the SPDX ontology/SHACL constraints. Worldshepherd's intake evaluator itself does not perform those validations.

### Published-example compatibility correction

The first internal fixture used conceptual model names (`Sbom`, `Package`, `packageVersion`, `packageUrl`). Testing against the SPDX project's published 3.0.1 example corpus caught that this is not the compact JSON-LD spelling used for Software-profile terms. Published examples use the namespace-prefixed aliases:

- `software_Sbom`;
- `software_Package`;
- `software_packageVersion`; and
- `software_packageUrl` when a package URL is present.

The adapter and regression fixtures were corrected before any `PROVEN INTERNALLY` promotion. A minimal regression modeled on the published `software/example13/spdx3.0/example13.spdx3.json` vocabulary must now pass, while the old unprefixed Software-profile spellings fail closed.

This compatibility test is still **not** SPDX conformance testing. It establishes only that the bounded parser recognizes the compact vocabulary observed in the official example corpus.

## Isolated third-party validator check

The dedicated CI gate also creates a temporary virtual environment and installs exactly:

`spdx3-validate==0.0.7`

The frozen fixture `tests/fixtures/spdx301_minimal.spdx3.json` is passed to that validator before the same fixture is evaluated by the Worldshepherd intake adapter.

SPDX's validation guidance lists `spdx3-validate` as a tool that performs JSON Schema and SHACL validation for SPDX 3 documents. Running that external tool inside Worldshepherd CI can establish only **third-party validator compatibility for the exact fixture and tool version executed**.

It does **not** establish:

- independent human review;
- community endorsement;
- conformance of arbitrary future SPDX inputs;
- conformance of the Worldshepherd product as an SPDX implementation;
- admission or release authority; or
- legal/license conclusions.

The validator is intentionally isolated from the SARA product environment so it does not become an undeclared runtime dependency.

## What the intake evaluator checks

`WS-SPDX-INTAKE-EVIDENCE-V1` performs only bounded local checks:

1. the official SPDX 3.0.1 context is present;
2. `@graph` is present and non-empty;
3. exactly one `SpdxDocument` exists;
4. at least one `software_Sbom` and one `software_Package` exist;
5. at least one `CreationInfo` declares SPDX 3.0.1;
6. relevant elements carry stable identifiers and creation-info references;
7. software packages carry names;
8. SPDX identifiers are unique within the input graph;
9. `element` and `rootElement` references from the document/SBOM resolve inside the graph;
10. the input object is unchanged by evaluation; and
11. package identity hints such as `software_packageVersion` and `software_packageUrl` are extracted only into a derived review projection.

## State transition

If every local check passes, the maximum state is:

`READY_FOR_HUMAN_ADMISSION_REVIEW`

This means only that the source is sufficiently coherent for a human to review it as input to a Worldshepherd admission decision.

It does **not** mean the software represented by the SBOM is admitted, trusted, safe, licensed correctly, vulnerability-free, supplier-approved, or releasable.

## Hard claims boundary

Even when every local check passes, the adapter hard-codes:

```text
spdx_conformance_established = false
json_schema_validation_established = false
semantic_ontology_validation_established = false
complete_sbom_established = false
license_legal_review_established = false
supplier_approval_established = false
admission_authorized = false
release_approved = false
external_validation_established = false
```

The source document remains authoritative. Worldshepherd's derived record is evidence about intake handling, not a replacement SPDX document.

## Questions for SPDX implementers

The September 2026 community review should focus on these questions:

1. Is preserving the original SPDX serialization by digest while producing a separate governed decision record the right interoperability boundary?
2. Which SPDX 3.x model elements should Worldshepherd rely on for component identity and supplier/provenance instead of inventing local aliases?
3. Should admission-policy decisions live entirely outside SPDX, or is there an existing SPDX mechanism/profile suitable for referencing those external decisions without changing source meaning?
4. Is `spdx3-validate` the validator/toolchain the community wants downstream implementers to pin for 3.0.1 structural + semantic validation, or should Worldshepherd use a different reference path?
5. Are there privacy or provenance pitfalls in retaining only package identifiers/PURLs plus the source-document digest in the Worldshepherd review projection?

A recommendation to delete local fields in favor of existing SPDX primitives is considered a successful review outcome.

## Claims state

`IMPLEMENTED IN SOFTWARE / SPDX COMMUNITY REVIEW PENDING`
