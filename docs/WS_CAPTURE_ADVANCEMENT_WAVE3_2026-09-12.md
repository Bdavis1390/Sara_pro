# Worldshepherd Capture Advancement — Wave 3

Date: 2026-09-12
Status: INTERNAL CAPTURE / READINESS DEVELOPMENT

## Purpose
Convert current high-value opportunity requirements into reusable Worldshepherd capability increments rather than one-off proposal work.

## Critical opportunity cluster

### NAVWAR APNT Open Topic — DON26BX05-NP004
Deadline: 2026-09-23 12:00 ET
Route: PRIME if SBIR/CSO eligibility and CMMC prerequisites are verified; otherwise PARTNER.
Required reusable increments:
- APNT status/confidence/threat/recovery data model
- API-first adapter layer
- containerized proof-of-concept deployment
- degraded-state workflow and operator decision support
- provenance for source, confidence, degradation, and recommended recovery action
- human authorization and action logging
Claims boundary: Worldshepherd has no current claim of Navy APNT certification, PNT hardware qualification, shipboard ATO, or CMMC status.

### NAVAIR CCA Post-Mission De-Brief/Re-Planning — DON26BZ05-NV074
Deadline: 2026-09-23 12:00 ET
Route: CONDITIONAL PRIME; PARTNER if eligibility/clearance path is insufficient.
Required reusable increments:
- evidence-backed post-mission state reconstruction
- uncertainty and confidence propagation
- multiple COA generation
- traceable rationale
- operator review/approval gate
- configuration-custodied mission replay
Claims boundary: no claim of operational CCA mission planning, classified integration, or Secret facility/personnel clearance.

### NAVAIR Digital-Twin CBM+ — DON26BZ05-DV087
Deadline: 2026-09-23 12:00 ET
Route: PARTNER unless Direct-to-Phase-II feasibility-equivalent evidence is verified.
Required reusable increments:
- high-rate telemetry reduction adapter
- digital-twin state synchronization
- diagnostics/prognostics evidence graph
- DDIL store-and-forward reconciliation
- explainability record for maintenance recommendation
- configuration/evidence lineage
Claims boundary: software architecture does not establish carrier-system CBM+ performance or DP2 eligibility.

### DIU Space Threat Intelligence Synthesis Engine — PROJ00716
Deadline: 2026-09-24 23:59:59 ET
Route: PARTNER unless clearance/facility pathway and commercial maturity are verified.
Required reusable increments:
- multi-INT ingestion abstraction
- provenance-preserving fusion
- confidence scoring
- knowledge-graph/semantic relation layer
- human-readable and machine-to-machine output surfaces
- model/data documentation package
Claims boundary: no claim of classified data access, operational missile warning, or space-threat prediction performance.

## New reusable mission packs

### APNT Decision Pack v0.1
Inputs: PNT source health, timing integrity, navigation confidence, interference/spoofing indicators, mission context.
Outputs: fused status, confidence, threat hypothesis, operational impact, recovery options, evidence references.
Mandatory controls: uncertainty retained; no silent source substitution; human approval for externally consequential action.

### Mission Replay & Replan Pack v0.1
Inputs: mission logs, sensor tracks, operator actions, platform state, objectives, constraints.
Outputs: reconstructed timeline, causal/evidence graph, COAs, confidence, tradeoffs, rationale, approval package.
Mandatory controls: distinguish observed facts from inferred state; preserve negative/anomalous evidence; no autonomous external execution without authorization.

### Digital-Twin Assurance Pack v0.2
Inputs: telemetry, configuration, maintenance history, simulation/twin state.
Outputs: synchronized twin state, anomalies, predicted failure hypotheses, uncertainty, maintenance options, evidence package.
Mandatory controls: model version and configuration digest required; prediction cannot be promoted to proven physical performance.

### Multi-INT Provenance Fusion Pack v0.1
Inputs: sensor/media/geospatial/report streams.
Outputs: entities, relations, tracks, conflicts, confidence, provenance, machine API, operator view.
Mandatory controls: retain source lineage; expose contradictory evidence; classify confidence separately from source authority.

## Cross-program engineering backlog
1. APNT canonical schema and mock adapters.
2. Containerized demo harness with offline/DDIL mode.
3. Signer-ready decision package generator.
4. Evidence graph with source/confidence/claims-state separation.
5. Mission replay event store and timeline reconstruction.
6. Multi-COA generator with explicit assumptions and uncertainty.
7. Digital-twin adapter interface with configuration digest.
8. Model/data card generator for government evaluation.
9. NIST 800-171/CMMC gap matrix with no implied compliance.
10. Partner/clearance gate registry.

## Capture doctrine update
Each qualifying opportunity must produce at least one reusable artifact, adapter, test, schema, or evidence record that raises readiness for multiple programs. Opportunity-specific code should be minimized unless a requirement cannot be represented through a reusable mission pack.
