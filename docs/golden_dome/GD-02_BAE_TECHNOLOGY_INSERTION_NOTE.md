# GD-02 — BAE Systems Technology-Insertion Note

**Target:** BAE Systems Aerospace & Mission Systems / RMWT-MEO Epoch 2 and adjacent mission-engineering work

**Status:** INTERNAL / NON-PROPRIETARY / NOT YET SUBMITTED

## Proposed insertion boundary
Worldshepherd should not compete with BAE's spacecraft bus, EO/IR payload, or flight-qualified tracking hardware. The proposed insertion boundary is the ground-side mission-assurance layer around heterogeneous observations, provenance, governed decision support, replay, degraded-state continuity, and interface evidence.

## Candidate evaluation package
Provide BAE an unclassified executable package that demonstrates:
1. deterministic replay of a synthetic multi-sensor mission thread;
2. source/configuration/result provenance with cryptographic hashes;
3. stale/conflicting-data identification;
4. confidence and independent-source gates;
5. identified-human approval before advisory dissemination;
6. explicit rejection of engagement/fire-control actions;
7. exportable audit evidence for engineering review.

## Questions for a BAE evaluator
- Which unclassified ground-system interface or surrogate event schema is appropriate for an initial plug-in evaluation?
- Which mission-assurance metrics matter most: traceability, latency, continuity, operator workload, interface conformance, or configuration custody?
- Is a synthetic replay package useful for an AMS technology-scouting, supplier, SBIR-support, IR&D, digital-engineering, or plugfest-style evaluation?
- What evidence package is required before BAE would accept an executable demonstration from a new small-business technology provider?

## Current evidence
Implemented repository components include synthetic mission replay, synthetic sensor fusion, evidence graphs, provenance, DDIL/rejoin logic, configuration custody, software provenance/SBOM tooling, policy gates, and qualification scaffolding. The Golden Dome G1 branch integrates a bounded subset into W-RMABM.

## Missing evidence before serious insertion discussion
- BAE-approved interface definition or surrogate;
- external reproduction of benchmark results;
- measured latency/load/failure-mode results;
- supplier cybersecurity/acquisition readiness evidence;
- data-rights and IP marking package;
- export-control determination;
- BAE engineering evaluation.

## Public program anchor
BAE states that Epoch 2 includes 10 spacecraft and a ground system delivering mission management, C2, and mission operations, and that its March 2026 PDR used model-based systems engineering and digital modelling/simulation. Source: https://www.baesystems.com/en-us/article/bae-systems-completes-preliminary-design-review-for-us-space-force-missile-warning-and-tracking-satellite-system

## External-safe statement
“Worldshepherd has an internally implemented synthetic mission-assurance prototype designed to preserve observation provenance, enforce human-authorized advisory workflows, and produce deterministic replay evidence. We are seeking an unclassified evaluation path; no BAE or government validation is currently claimed.”
