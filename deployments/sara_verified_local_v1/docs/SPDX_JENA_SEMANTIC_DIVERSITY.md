# SPDX 3.0.1 Semantic Engine Diversity — Apache Jena Cross-Check

## Purpose

This experiment tests whether two genuinely different SHACL implementation lineages agree on the exact SPDX 3.0.1 semantic control already proven in Worldshepherd:

- **pySHACL** — Python / RDFLib lineage; and
- **Apache Jena SHACL** — Java / Apache Jena lineage.

The experiment is deliberately isolated from the already validated SPDX intake, structural triangulation, and semantic-negative PRs.

## Why this is different from the earlier triangulation

`spdx3-validate` uses pySHACL for semantic validation, so comparing `spdx3-validate` with direct pySHACL execution did not establish independent semantic-engine diversity.

Apache Jena provides a separately implemented W3C SHACL engine. Jena 6.2.0 documents support for SHACL Core and SHACL SPARQL Constraints.

The SPDX project's current validation guidance names pySHACL as a known SHACL command-line validator; it does not currently list Jena. Therefore Jena is used here only as an independent semantic cross-check, **not** as an SPDX-recommended validator.

## Exact control

The gate uses the same two inputs as the proven semantic-negative control:

1. baseline SPDX 3.0.1 JSON-LD fixture in which `CreationInfo.createdBy` references a `Person` / `Agent`; and
2. a mutation in which only `CreationInfo.createdBy` is changed to reference the existing `software_Package`.

The canonical SPDX 3.0.1 SHACL model is fetched from:

`https://spdx.org/rdf/3.0.1/spdx-model.ttl`

and must match the already pinned SHA-256:

`30ebb4af2d70a9809044ef46f44cc3dc5125226d70f818a50ed2e1d5f404c593`

## Jena execution path

The gate:

1. installs Java 21;
2. downloads Apache Jena 6.2.0 from the Apache distribution site;
3. verifies the Jena archive against Apache's published SHA-512 sidecar;
4. parses both JSON-LD inputs with Jena RIOT;
5. explicitly merges quad-capable JSON-LD input into a complete triples validation graph and writes N-Triples;
6. proves the expected `createdBy` object survives that projection in both baseline and mutation;
7. runs Jena `shacl validate --text` against the canonical SPDX model;
8. requires the baseline report to be exactly `Conforms`;
9. requires the mutation report to contain a semantic violation rather than `Conforms`; and
10. independently runs pySHACL on the original JSON-LD inputs and requires the same baseline/negative result.

This keeps RDF parsing and semantic validation of the Jena path within Jena's Java stack rather than feeding it RDF produced by pySHACL/RDFLib.

### Quad-projection correction

The first Jena experiment used RIOT JSON-LD input with triples-only Turtle output **without** `--merge`. RIOT emitted a warning that the input contained quads while triple output was requested. Jena's own command implementation documents that, in this mode, quads are ignored rather than merged into the triples output.

That made the first result invalid as a semantic-engine comparison: Jena reported `Conforms` for the negative control because the validation graph had lost relevant quad data before SHACL evaluation.

The corrected gate now uses:

```text
riot --merge --syntax=JSONLD11 --output=NTRIPLES
```

and hard-fails unless the baseline projection contains a `createdBy` triple referencing the expected Person and the mutated projection contains a `createdBy` triple referencing the expected Package.

The initial false-conformance observation is therefore classified as **HARNESS DEFECT / QUAD-TO-TRIPLE DATA LOSS**, not as evidence that Jena and pySHACL disagree semantically.

## Release-integrity boundary

The Jena binary archive is checked against Apache's published SHA-512 sidecar. The gate does **not** currently verify the Apache PGP release signature.

Therefore the evidence record retains:

`release_artifact_pgp_signature_verified = false`

Checksum verification establishes download integrity against the published sidecar; it is not a claim of a cryptographically independent provenance chain.

## Maximum positive evidence state

If the corrected engines agree on both exact controls, the maximum state is:

`EXACT_CONTROL_SEMANTIC_ENGINE_AGREEMENT`

with:

`semantic_engine_diversity_established_for_exact_control = true`

This statement is intentionally scoped to the exact baseline and wrong-range mutation. It does not imply that the two engines agree across the full SPDX SHACL model or all future inputs.

## Hard exclusions

Even after a passing gate:

```text
jena_is_spdx_recommended_validator = false
general_spdx_conformance_established = false
arbitrary_input_conformance_established = false
independent_external_validation_established = false
community_endorsement_established = false
release_artifact_pgp_signature_verified = false
admission_authorized = false
release_approved = false
```

## Claims state

`IMPLEMENTED IN SOFTWARE / CORRECTED JENA CROSS-CHECK CI PENDING`
