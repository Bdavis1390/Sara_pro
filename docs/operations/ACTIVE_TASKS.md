# Worldshepherd Active Tasks

**Status:** `CANONICAL`

**As of:** 2026-09-15

Worldshepherd uses exactly **three top-level operating umbrellas**. Detailed issues, pull requests, opportunity ledgers, research threads, and subsystem work remain child work; they do not become new top-level priorities simply because they are numerous.

## ACTIVE 1/3 — Platform & Assurance

**GitHub:** #281

Owns the software/system foundation and its trustworthiness:

- SARA runtime and orchestration
- PRIME SENTINEL authorization and policy boundaries
- ECHO SENTINEL LINK provenance/evidence custody
- OVERWATCH observability/common-operating-picture work
- cybersecurity, dependency hygiene, SBOM/provenance, release evidence
- reproducibility, recovery, rollback, configuration custody
- CI quality, repository architecture, documentation source-of-truth control
- branch/PR freshness and supersession hygiene
- external technical-review readiness

### Current focal state

- Canonical SARA runtime normalization is complete on `main` through PR #288.
- Issue #287 is closed by that merge.
- PR #279 remains an active **RECONCILE_REQUIRED** external-review/readiness work package. Its useful security/reproducibility/review material must be forward-ported onto current `main` before reviewer outreach.
- CI action/runtime dependencies must be kept on supported upstream versions without weakening existing checks.

## ACTIVE 2/3 — Science & Validation

**GitHub:** #282

Owns falsifiable technical and physical evidence:

- physics/model validation
- RF/metasurface research
- materials/meta-alloy and DED work
- propulsion and energy research
- space systems and particulate/resource characterization
- robotics, humanoid, drone and VTOL physical qualification
- APNT and resilient-communications measured performance
- hardware/RTL verification where physical implementation is implicated
- scientific negative evidence, uncertainty, calibration and replication

### Operating rule

A dated experiment, simulation, benchmark, or evidence artifact is not "stale" merely because it is old. It remains historical evidence. New evidence may supersede its interpretation or maturity claim, but the original record should remain addressable.

Branches and PRs with unique scientific work are preserved until their evidence is either incorporated, explicitly superseded, or archived with provenance intact.

## ACTIVE 3/3 — Growth & Externalization

**GitHub:** #283

Owns outward-facing capture and transition:

- government opportunity intelligence and submissions
- partner discovery and validation
- outreach and external review
- revenue/capture pathways
- licensing/commercialization preparation
- institutional adoption and teaming
- public portfolio positioning

### Freshness rule

Opportunity status, deadlines, contacts, program facts, partner availability and submission requirements are time-sensitive. Active capture material must be re-verified against authoritative sources before external use. Outreach is not partner validation; a draft is not a sent communication; interest is not revenue.

## Routing table

| Work item | Top-level owner |
|---|---|
| Runtime, CI, security, governance, provenance | #281 |
| Branch/PR/document freshness and supersession | #281 |
| Physical experiments, simulation validity, hardware qualification | #282 |
| Research branches with unresolved scientific claims | #282 |
| Solicitations, deadlines, partners, outreach, capture | #283 |
| Cross-domain item | one primary umbrella; reference the others as dependencies |

## Anti-inflation rules

1. Do not create another top-level task when an item fits #281, #282 or #283.
2. Child issues may remain open as detailed evidence/capture ledgers.
3. The umbrella issue determines priority; child issue age does not imply abandonment.
4. A pull request that falls behind `main` is not automatically stale; classify it `RECONCILE_REQUIRED` if it still contains unique useful work.
5. A superseded branch/PR must identify its successor before closure where practical.
6. Historical evidence is retained rather than silently rewritten.
7. Claims maturity can only move forward when evidence improves.

## Source-of-truth rule

When a child issue, branch README, old PR body, or dated document conflicts with a current canonical document or tested implementation, the current canonical artifact and its commit-scoped evidence govern. Preserve the older material as history and record the supersession explicitly.
