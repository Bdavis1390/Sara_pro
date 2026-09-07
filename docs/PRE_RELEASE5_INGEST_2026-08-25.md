# PRE Release-5 Ingest — 2026-08-25

Claims-controlled ingest. Navy topic pages below identify themselves as unofficial copies of the DoW BAA; operative submission requirements must be checked against DSIP/DoW before proposal freeze.

## Source lineage
Retrieved 2026-09-02T17:38:00Z.

- DON26BX05-NP004 — Navy SBIR/STTR Topic: Unified Assured PNT Operational Awareness and Decision Support — https://navysbir.com/n26_5/DON26BX05-NP004.htm
- DON26BX05-NP003 — Navy SBIR/STTR Topic: AI/ML Legacy Data to MBSE — https://navysbir.com/n26_5/DON26BX05-NP003.htm
- DON26BZ05-NV078 — Navy SBIR/STTR Topic: Technical Data Transformation / IETM — https://navysbir.com/n26_5/DON26BZ05-NV078.htm
- DON26BZ05-NV072 — Navy SBIR/STTR Topic: Digitally Enhanced Weapon System Technical Data — https://navysbir.com/n26_5/DON26BZ05-NV072.htm
- DON26BZ05-NV074 — Navy SBIR/STTR Topic: Automated CCA Post-Mission Debrief and Replanning — https://navysbir.com/n26_5/DON26BZ05-NV074.htm

These are government-hosted secondary topic reproductions used for requirement discovery and traceability. Direct DSIP/DoW solicitation review remains the authoritative proposal-freeze gate.

## PRE-RD-2026-0001 — APNT operator decision assurance
- Demand: CONFIRMED_DEMAND
- Topic: DON26BX05-NP004
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending direct DSIP freeze check
- Horizon: 0-90D
- Requirement: modular/API-first APNT awareness software; containerization-ready; health/confidence/threat/degradation/operational-impact/recovery presentation; operator decision support.
- Existing WS capability: SARA workflow/registry — IMPLEMENTED IN SOFTWARE in the repository's bounded tested scope. ECHO, PRIME, and OVERWATCH named-component implementation status — NOT CURRENTLY CLAIMED absent repository-retained evidence establishing those components as separately implemented services.
- Missing: ASPN/pntOS/GPNTS integration, calibrated APNT data, Navy operator validation.
- Build now: synthetic APNT scenario + confidence/provenance graph + DDIL campaign + recovery authorization + operator-task metrics.

## PRE-RD-2026-0002 — Legacy evidence to MBSE
- Demand: CONFIRMED_DEMAND
- Topic: DON26BX05-NP003
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending direct DSIP freeze check
- Horizon: 0-90D
- Requirement: ingest heterogeneous legacy artifacts and generate accurate SysML/Cameo models supporting design, cyber, interfaces, test, configuration, reliability and certification.
- Existing WS capability: SARA workflow/registry and repository-retained qualification/provenance primitives — IMPLEMENTED IN SOFTWARE only where directly exercised by tests. Automatic document-to-model reconstruction — NOT CURRENTLY CLAIMED.
- Missing: validated automatic SysML reconstruction and Cameo/MagicDraw interoperability — NOT CURRENTLY CLAIMED.
- Build now: synthetic ground-truth system + mixed artifact corpus + evidence graph + relationship extraction + neutral model + SysML export + precision/recall/coverage metrics.
- Qualification dependencies: projected CMMC L2 Self; ITAR/EAR; advanced phases may require Secret FCL/PCL and U.S.-owned/operated/no-foreign-influence conditions or approved mitigation.

## PRE-RD-2026-0003 — Technical-data transformation/IETM
- Demand: CONFIRMED_DEMAND
- Topic: DON26BZ05-NV078
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending direct DSIP freeze check
- Horizon: 0-90D
- Requirement: transform diverse Navy TMs to XML/IETM-compatible output while preserving distribution/DFARS markings; support PDF, MIL-STD-3001-1, MIL-DTL-81310, S1000D 3.0/4.0; later NLP/search and step-by-step AR/XR workflows.
- Existing WS capability: bounded SARA ingestion/workflow and qualification-evidence patterns — IMPLEMENTED IN SOFTWARE only where repository tests retain evidence. Standards-compliant IETM transformation — NOT CURRENTLY CLAIMED.
- Missing: standards conversion coverage, viewer compatibility, production accuracy — NOT CURRENTLY CLAIMED.
- Build now: shared evidence graph with MBSE lane + XML/schema adapter + marking inheritance + human ambiguity review + conversion metrics.
- Government Phase-II target captured from the cited topic page: >=95% conversion accuracy and <=1% error after correction; this is a future validation target, not current WS performance.

## PRE-RD-2026-0004 — Digitally enhanced weapon-system technical data
- Demand: CONFIRMED_DEMAND
- Topic: DON26BZ05-NV072
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending full topic/direct-DSIP ingest
- Horizon: 0-90D / 3-12M reuse
- Signal: Digital Engineering, MBSE, IETM, Digital Twin, Technical Data Management and Predictive Maintenance recur together.
- Existing WS capability: bounded repository workflow/qualification primitives only — IMPLEMENTED IN SOFTWARE where tested; domain-specific digital-thread performance — NOT CURRENTLY CLAIMED.
- Action: ingest full authoritative topic before role determination; reuse Evidence Graph + Technical Data Transformation Pipeline as internal architecture candidates only.

## PRE-RD-2026-0005 — Post-mission autonomy evidence/replanning
- Demand: CONFIRMED_DEMAND
- Topic: DON26BZ05-NV074
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending full topic/direct-DSIP ingest
- Horizon: 0-90D / 3-12M reuse
- Signal: automated post-mission debrief and replanning for collaborative/autonomous platforms reinforces mission replay, provenance and controlled replanning as reusable PRE capabilities.
- Existing WS capability: bounded SARA workflow and synthetic qualification/replay patterns — IMPLEMENTED IN SOFTWARE where repository tests retain evidence. OVERWATCH/ECHO/PRIME named-component implementation and CCA operational performance — NOT CURRENTLY CLAIMED absent separate evidence.
- Action: ingest full authoritative topic and benchmark synthetic mission replay, evidence lineage, and human-authorized replanning without implying CCA or Navy validation.

## Cross-topic forecast
Demand recurrence supports building one governed Evidence Graph / Qualification Compiler rather than one-off opportunity implementations.

Shared canonical pipeline:
`source artifact/sensor/event -> normalized evidence graph -> domain projection -> validation -> human/policy review/release -> replayable qualification bundle`

Domain projections currently prioritized:
1. APNT operational picture
2. SysML/MBSE
3. XML/IETM
4. mission replay/replanning
5. digital twin/CBM+
6. network/configuration assurance

No domain projection inherits physical, operational, compliance or certification validity merely because the shared software pipeline exists.
