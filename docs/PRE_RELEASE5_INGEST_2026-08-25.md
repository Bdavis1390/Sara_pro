# PRE Release-5 Ingest — 2026-08-25

Claims-controlled ingest. Navy pages below identify themselves as unofficial copies of the DoW BAA; operative submission requirements must be checked against DSIP/DoW before proposal freeze.

## PRE-RD-2026-0001 — APNT operator decision assurance
- Demand: CONFIRMED_DEMAND
- Topic: DON26BX05-NP004
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending direct DSIP freeze check
- Horizon: 0-90D
- Requirement: modular/API-first APNT awareness software; containerization-ready; health/confidence/threat/degradation/operational-impact/recovery presentation; operator decision support.
- Existing WS capability: SARA workflow/registry, ECHO provenance model, PRIME authorization, OVERWATCH visualization patterns — IMPLEMENTED IN SOFTWARE where retained evidence exists.
- Missing: ASPN/pntOS/GPNTS integration, calibrated APNT data, Navy operator validation.
- Build now: synthetic APNT scenario + confidence/provenance graph + DDIL campaign + recovery authorization + operator-task metrics.

## PRE-RD-2026-0002 — Legacy evidence to MBSE
- Demand: CONFIRMED_DEMAND
- Topic: DON26BX05-NP003
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending direct DSIP freeze check
- Horizon: 0-90D
- Requirement: ingest heterogeneous legacy artifacts and generate accurate SysML/Cameo models supporting design, cyber, interfaces, test, configuration, reliability and certification.
- Existing WS capability: workflow/provenance/governance primitives — IMPLEMENTED IN SOFTWARE.
- Missing: validated automatic SysML reconstruction and Cameo/MagicDraw interoperability — NOT CURRENTLY CLAIMED.
- Build now: synthetic ground-truth system + mixed artifact corpus + evidence graph + relationship extraction + neutral model + SysML export + precision/recall/coverage metrics.
- Qualification dependencies: projected CMMC L2 Self; ITAR/EAR; advanced phases may require Secret FCL/PCL and U.S.-owned/operated/no-foreign-influence conditions or approved mitigation.

## PRE-RD-2026-0003 — Technical-data transformation/IETM
- Demand: CONFIRMED_DEMAND
- Topic: DON26BZ05-NV078
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending direct DSIP freeze check
- Horizon: 0-90D
- Requirement: transform diverse Navy TMs to XML/IETM-compatible output while preserving distribution/DFARS markings; support PDF, MIL-STD-3001-1, MIL-DTL-81310, S1000D 3.0/4.0; later NLP/search and step-by-step AR/XR workflows.
- Existing WS capability: ingestion/workflow/provenance/review patterns — IMPLEMENTED IN SOFTWARE where evidenced.
- Missing: standards conversion coverage, viewer compatibility, production accuracy — NOT CURRENTLY CLAIMED.
- Build now: shared evidence graph with MBSE lane + XML/schema adapter + marking inheritance + human ambiguity review + conversion metrics.
- Government Phase-II target captured: >=95% conversion accuracy and <=1% error after correction; this is a future validation target, not current WS performance.

## PRE-RD-2026-0004 — Digitally enhanced weapon-system technical data
- Demand: CONFIRMED_DEMAND
- Topic: DON26BZ05-NV072
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending full topic ingest
- Horizon: 0-90D / 3-12M reuse
- Signal: Digital Engineering, MBSE, IETM, Digital Twin, Technical Data Management and Predictive Maintenance recur together.
- Action: ingest full topic before role determination; reuse Evidence Graph + Technical Data Transformation Pipeline.

## PRE-RD-2026-0005 — Post-mission autonomy evidence/replanning
- Demand: CONFIRMED_DEMAND
- Topic: DON26BZ05-NV074
- Source status: GOVERNMENT_SECONDARY_VERIFIED pending full topic ingest
- Horizon: 0-90D / 3-12M reuse
- Signal: automated post-mission debrief and replanning for collaborative/autonomous platforms reinforces mission replay, provenance and controlled replanning as reusable PRE capabilities.
- Action: ingest full topic and benchmark against OVERWATCH replay + ECHO event lineage + PRIME replanning authorization.

## Cross-topic forecast
Demand recurrence supports building one governed Evidence Graph / Qualification Compiler rather than one-off opportunity implementations.

Shared canonical pipeline:
`source artifact/sensor/event -> normalized evidence graph -> domain projection -> validation -> PRIME review/release -> replayable qualification bundle`

Domain projections currently prioritized:
1. APNT operational picture
2. SysML/MBSE
3. XML/IETM
4. mission replay/replanning
5. digital twin/CBM+
6. network/configuration assurance

No domain projection inherits physical, operational, compliance or certification validity merely because the shared software pipeline exists.
