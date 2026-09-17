# Finding: The Semantic Snapshot Gap

## Core result

The version-skew problem first found in ancient-text translations is a general information-integrity problem:

> **Native version identifiers often track only a subset of meaning-bearing changes.**

Therefore:

**identifier.version is not necessarily a complete semantic snapshot.**

## Scientific database example — RefSeq

NCBI documents that a RefSeq record's version number changes when the underlying sequence changes, while annotation or associated-publication updates do not necessarily trigger that same version change.

For human reference annotation, NCBI separately tracks annotation releases and states that annotation is recalculated with each update. The annotation release number can be cited.

A particularly sharp example is the WP_ non-redundant protein family: the exact sequence is immutable and the record version remains ".1", but the protein name and descriptive annotation can still be maintained and updated.

### Consequence

A workflow that stores only:

`WP_xxxxx.1`

can reproduce the sequence identity while failing to reproduce the historical annotation that informed a scientific interpretation.

The proper reproducibility tuple is closer to:

`(sequence_accession.version, annotation_release_or_timestamp, content_hash)`.

## Medical knowledge example — ClinVar

ClinVar explicitly warns that classification may change over time and recommends citing accession **and version**. Submitted SCV records increment their version when classification or other substantive fields are updated.

But another layer exists: the ClinVar website is updated weekly while a VCF distribution is monthly. ClinVar's FAQ explicitly notes that a web record can therefore be newer than the corresponding monthly VCF.

### Consequence

Two analysts can truthfully say "I used ClinVar" and still operate on different semantic states.

A medical-data pipeline must therefore pin:

`record accession.version + release date + surface/file type + review/evaluation date`.

This is a data-integrity observation, not patient-specific medical advice.

## Legal example — Supreme Court opinions

The U.S. Supreme Court publishes opinions first as slip opinions, provides explicit links to revisions, and later replaces them with edited United States Reports publication states.

### Consequence

A legal quotation from a slip opinion should retain the exact revision state or text snapshot. Docket number alone is not sufficient to reproduce wording.

## Intelligence-analysis example

ICD 203 requires analysts to distinguish underlying intelligence from assumptions and judgments, explain uncertainty, and identify indicators that would alter judgments.

### Consequence

A judgment is a derived semantic layer. If a linchpin assumption or underlying source changes, preserving the report identifier is insufficient; the dependency chain must be reassessed.

## Software-documentation example

GitHub's REST API is explicitly date-versioned, and breaking changes are released in new versions. Requests without an explicit API-version header can default to an older version. Kubernetes likewise deprecates and removes API versions, sometimes changing defaults and field structure.

### Consequence

Code, documentation, schema, and runtime must be version-bound together. A documentation URL without runtime/API version is an incomplete dependency reference.

## Historical-archive example

NARA states that its Catalog is regularly updated with new descriptions and digital objects.

### Consequence

An archival identifier can remain stable while the discoverable descriptive layer evolves. Historical claims that depend on a catalog description should store the description snapshot/timestamp rather than only the archival ID.

## General architecture

For any evidence object E, define a semantic snapshot:

`S(E) = ID + native_version + content_hash + annotation/schema release + timestamp + publication state + domain-specific dependencies`.

A derived claim C stores:

`C.depends_on = hash(S(E))`.

When S(E) changes, C becomes:

`REVALIDATION_REQUIRED`

rather than silently remaining current.

## Why this matters

This turns provenance from a citation problem into a dependency-management problem.

The same mechanism that protects ancient translations can protect:
- scientific interpretation;
- clinical-data pipelines;
- legal quotation and secondary analysis;
- intelligence judgments;
- software integrations;
- archival/historical claims.

ATIP has therefore exposed a general-purpose evidence-integrity architecture rather than a niche ancient-text feature.
