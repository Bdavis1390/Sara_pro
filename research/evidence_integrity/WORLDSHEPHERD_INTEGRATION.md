# EBOM Integration Across Worldshepherd

## SARA

For any consequential analysis, SARA emits an Evidence Bill of Materials alongside the prose result.

SARA must record:
- source snapshots;
- intermediate transformations;
- assumptions;
- model/tool versions where material;
- downstream claim nodes.

A conclusion without an EBOM remains draft-level for high-consequence workflows.

## ECHO SENTINEL LINK

ECHO stores:
- immutable source fingerprints;
- semantic snapshots;
- source-change events;
- dependency edges;
- negative evidence;
- revalidation outcomes.

When an upstream fingerprint changes, ECHO computes the transitive blast radius.

## PRIME SENTINEL

PRIME fails closed when:
- a material ancestor is REVALIDATION_REQUIRED;
- a source is unversioned where semantic snapshotting is required;
- a provisional legal/software/medical/scientific source is presented as final;
- an intelligence judgment's linchpin assumption changed without reassessment;
- a translation/interpretation depends on a superseded witness.

## OVERWATCH

OVERWATCH should expose:
- current claims;
- stale claims;
- upstream change events;
- blast radius by project/domain;
- revalidation queue;
- unresolved assumptions;
- claim state before/after revalidation.

## Domain triggers

### Science
Trigger on:
- annotation release change;
- sequence/reference change;
- schema change;
- corrected/retracted source.

### Medical knowledge
Trigger on:
- ClinVar accession/version update;
- expert-panel or aggregate classification change;
- release-date mismatch across data surfaces;
- guideline/label revision.

### Legal
Trigger on:
- slip-opinion revision;
- superseding opinion/publication state;
- amended statute/regulation;
- corrected official text.

### Intelligence
Trigger on:
- new source contradicting key evidence;
- linchpin assumption invalidated;
- indicator defined in the assessment is observed;
- source confidence materially changes.

### Software
Trigger on:
- API/runtime version mismatch;
- deprecated/removed endpoint;
- schema breaking change;
- documentation snapshot differs from deployed version.

### Historical archives
Trigger on:
- catalog description update;
- newly digitized object linked;
- creator/date/identity metadata revision;
- new primary source supersedes secondary description.

## General doctrine

A citation tells us where a claim came from.

An EBOM tells us **what must remain true for the claim to remain current**.
