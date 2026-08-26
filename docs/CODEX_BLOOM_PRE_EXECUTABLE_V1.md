# Worldshepherd Codex Bloom — Executable PRE Architecture v1

Status: IMPLEMENTED IN SOFTWARE where named modules/tests exist on `pre/release5-ingest-build`; all domain, physical, compliance, certification, partner and operational claims remain separately evidence-gated.

## Canonical governed pipeline

`source -> adapter -> normalization -> Evidence Graph -> bounded algorithm/domain projection -> PRIME action/release gate -> Qualification Evidence -> OVERWATCH/replay -> human review`

The same chain is intended to serve APNT, MBSE, technical data/IETM, mission replay, sensor fusion, digital twins, autonomy, RF analytics and manufacturing provenance without allowing evidence from one domain to silently validate another.

## Core executable services

### PRE requirement model
- `qualification.py`
- independent SOURCE STATUS and WORLDSHEPHERD CAPABILITY STATUS
- requirement-delta records
- evidence scopes and supersession states
- deterministic bundle digest
- fail-closed physical `PROVEN_INTERNALLY` rule

### Evidence Graph
- node/edge model
- source references
- confidence fields
- referential-integrity validation
- graph precision/recall scorer

### Artifact and expected-result contracts
- `evidence_artifacts.py`
- SHA-256 artifact identity
- required input/output/log/config/source roles
- explicit expected-result operators and thresholds
- tamper detection
- `qualification_eval.py` fail-closes missing metrics

### PRIME bounded action gate
- `prime.py`
- PROPOSED -> APPROVED / DENIED / OVERRIDDEN
- identified reviewer required for decisions
- approved/overridden actions can be REVOKED
- not a government authorization or certified safety controller

### DDIL qualification harness
- `ddil.py`, `ddil_campaign.py`
- packet drop
- added latency
- reordering
- stale data
- duplication
- deterministic replay evidence
- synthetic software transport behavior only; no RF/tactical-network readiness claim

### Dynamic Mission Enclave / Common Services contract
- `common_services.py`
- versioned service manifests
- interface version
- software/SBOM digests
- authority requirement
- platform-adapter registration
- rollback history
- prototype registry only; no flight/platform certification

### Compliance readiness evidence
- `compliance.py`
- UNKNOWN default
- PRESENT requires evidence refs
- GAP and NOT_APPLICABLE states
- authoritative assessment reference separated from internal readiness
- no CMMC/NIST 800-171 compliance claim without authoritative evidence

## APNT projection

Modules:
- `apnt_adapter.py`
- `apnt.py`
- `apnt_qualification.py`
- fixture `WS-APNT-SYNTH-001`

Implemented:
- normalized synthetic GNSS/INS/alternate-PNT-like source contract
- explicit ASPN mapping stub that fails closed
- nominal/degraded/GNSS-denied/recovery awareness model
- recovery-option candidate set
- source -> state -> recovery Evidence Graph
- replayable synthetic qualification bundle

Not established:
- ASPN/pntOS/GPNTS interoperability
- navigation solution accuracy
- sensor fusion performance
- Navy operator effectiveness
- shipboard deployment
- CMMC/authorization

## MBSE projection

Modules:
- `legacy_normalization.py`
- `mbse_extract.py`
- `graph_metrics.py`
- fixture `WS-MBSE-SYNTH-001`

Implemented:
- source-preserving normalization for current synthetic text/BOM/network/cable artifact types
- conservative rule-based extraction of only explicit supported relationships
- source refs and confidence on extracted edges
- graph construction
- precision/recall/unsupported/missed scoring framework

Not established:
- general AI/ML document understanding
- PDF/image/diagram extraction
- SysML/XMI export
- Cameo/MagicDraw interoperability
- Navy/Aegis reconstruction performance
- classified-data handling

## Qualification ladder

1. SCHEMA — object validates.
2. FIXTURE — frozen synthetic input and expected result exist.
3. INTERNAL SOFTWARE — deterministic test passes and evidence bundle is retained.
4. SIMULATION — representative simulation is validated against stated limits.
5. HIL — real hardware interface is exercised.
6. PHYSICAL LAB — measured physical performance exists.
7. PARTNER — external hardware/data/facility evidence is retained.
8. INDEPENDENT — third-party/government test evidence exists.
9. COMPLIANCE/CERTIFICATION — authoritative assessment/certification applies to defined scope.
10. OPERATIONAL — relevant operational environment evidence exists.

No rung inherits the next rung automatically.

## Cross-opportunity reuse matrix

| Capability | APNT | MBSE | IETM | C2/MOSA | Sensor Fusion | Autonomy | CBM+/Twin | RF | Manufacturing |
|---|---|---|---|---|---|---|---|---|---|
| Evidence Graph | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| Qualification Compiler | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| PRIME gate | yes | release | release | yes | yes | yes | maintenance | model release | process release |
| DDIL harness | yes | optional | optional | yes | yes | yes | yes | yes | remote ops |
| Artifact hashing | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| Common Services | yes | ingest | ingest | primary | primary | primary | primary | deployment | provenance |

## Current P0 gaps

1. real APNT adapter mapping using authoritative ASPN/pntOS definitions
2. APNT operator UI and scripted human-effectiveness study
3. packet partition/rejoin and conflict-reconciliation DDIL cases
4. persistent Common Services registry integrated with SARA storage/audit
5. MBSE PDF/image/diagram parsers
6. MBSE neutral intermediate model + SysML/XMI export
7. IETM/S1000D projection and marking inheritance
8. CMMC/NIST control-evidence inventory from authoritative company records
9. third live-opportunity demonstrator consuming the same qualification schema
10. independent clean-environment reproduction artifact

## Claims-control rule

Prediction drives preparation. Synthetic evidence can establish only synthetic software behavior. Internal software tests can establish only the exact implemented/tested software behavior. Physical, platform, operator, compliance, certification and operational claims require corresponding evidence and are not inferred from architectural fit.
