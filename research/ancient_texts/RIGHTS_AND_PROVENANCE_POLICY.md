# ATIP Rights & Provenance Policy

## Canonical rule

A text may be **referenced** without being locally copied. Canonical ingestion is split into:

1. metadata/reference ingestion;
2. transcription ingestion;
3. translation/commentary ingestion;
4. image/media ingestion.

Each layer has an independent rights decision.

## Rights states

- `OPEN_REUSE` — explicit open license supports intended reuse.
- `PUBLIC_ACCESS_LIMITED_REUSE` — publicly viewable, but reuse/bulk rights are restricted or unclear.
- `PERMISSION_REQUIRED` — canonical record may store identifiers and links only.
- `UNKNOWN` — fail closed; no local copy until verified.

## Provenance priority

A. Primary object/manuscript + authoritative repository.
B. Scholarly corpus / critical edition.
C. Curatorial description.
D. Scholarly secondary work.
E. Reception-history / modern interpretation.
F. Unsourced attribution.

E/F material can document **what later people claimed**, but cannot silently populate ancient provenance, translation or original-meaning fields.

## Immutability

- source images/transcriptions receive checksums where possible;
- diplomatic transcription is append-only;
- normalization is a derived layer;
- editorial reconstruction is explicit;
- translations are versioned and attributed;
- later interpretations cannot overwrite earlier witnesses.

## Conflict handling

When witnesses disagree, retain all variants and the relation:
`VARIANT_OF`, `COPIED_FROM`, `EDITORIAL_RECONSTRUCTION_OF`, or `UNRESOLVED`.

No "best text" is substituted silently for the actual witness.
