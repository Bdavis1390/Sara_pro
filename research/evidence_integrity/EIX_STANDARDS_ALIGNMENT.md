# Evidence Impact Exchange — Standards Alignment

EIX does not replace existing provenance, publication-status, or vulnerability-exploitability standards. It composes their ideas at the **claim-dependency layer**.

## W3C PROV

Relevant concepts:
- `prov:wasRevisionOf`
- `prov:wasInvalidatedBy`
- entity/activity provenance
- derivation and quotation

ATIP/EIX extension:
- W3C PROV can represent that an evidence entity was revised or invalidated.
- EBOM records which Worldshepherd claims depend on that entity.
- EIX records whether each dependent claim is actually affected.

## Crossref Crossmark

Crossmark reports current content status including corrections, updates, and retractions, and is explicitly intended to alert readers even when an article/PDF has been downloaded earlier.

ATIP/EIX extension:
- Crossmark-style event -> ECHO change event.
- EBOM -> downstream claim blast radius.
- EIX -> per-claim applicability assessment.

## PubMed / NLM

NLM creates links between original articles and retraction notices.

ATIP/EIX extension:
- Retraction link is a high-severity change event.
- Dependent claims are quarantined until materiality is assessed.
- A retraction does not automatically imply that every factual statement ever quoted from the paper is false; the affected claim scope must be recorded.

## SPDX VEX analogy

VEX distinguishes the existence of a vulnerability from whether a particular product is affected.

EIX applies the same discipline to evidence:
- an upstream change exists;
- a dependent claim may or may not be affected;
- "not affected" requires explicit rationale/evidence;
- uncertainty remains under review rather than being silently cleared.

## Safety-critical rule

"NOT_AFFECTED" is never inferred from absence of evidence.
It requires an explicit applicability assessment.
