# ATIP Federated Architecture

## Why federation

No single database contains every ancient text, and licensing differs sharply across projects. ATIP therefore operates as a **federation of source-aware adapters**, not a scraper that flattens provenance.

## Pipeline

```
source registry
   |
rights/provenance gate
   |
adapter
   |
raw witness/reference layer
   |
normalization + checksum
   |
text/layout segmentation
   |
ATIP canonical record
   |
evidence graph
   |
benchmark / null models
   |
SARA reasoning record
   |
PRIME claim gate
   |
ECHO evidence + negative-evidence ledger
   |
OVERWATCH maturity dashboard
```

## Adapter contract

Every adapter must emit:

- source authority
- stable identifier / accession
- source URL
- rights state
- date/place/material
- script/language with confidence
- raw/diplomatic transcription when permitted
- normalization as a separate field
- translation attribution
- image reference rather than copy when rights require
- source checksum/version
- decipherment status
- uncertainties and editorial interventions

## Corpus-wide analyses

The graph layer enables comparisons that ordinary full-text search misses:

- repeated formulae across corpora;
- spatial/layout parallels;
- sign-position constraints;
- scribal drift;
- translation drift;
- intertextual borrowing;
- chronology/contact constraints;
- motif topology;
- calendrical/numerical structure;
- observer-context effects.

Candidate discovery is allowed to be broad. Claim promotion is narrow.

## Scale targets

- Phase A: 1,000 provenance-complete records.
- Phase B: 10,000 multi-corpus records.
- Phase C: corpus-level ingestion for sources with lawful machine access.
- Phase D: reproducible cross-corpus benchmark publication.

The program intentionally prefers 1,000 auditable records over 1,000,000 provenance-flattened records.
