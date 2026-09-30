# WS-QX 0.1 Software Interface

`qx_evidence.py`

- `digest(value)` — deterministic SHA-256 namespaced digest for JSON-serializable evidence structures.
- `EvidenceVector` — separate physical-performance, assurance/TEVV, and replication/external states.
- `QualificationEnvelope` — common qualification evidence record.
- `finalize_internal()` — evaluates structural/internal prerequisites and deliberately leaves higher claims false.
- `promote_physical()` — requires internal qualification, hardware/calibration identities, observed physical I/O, verified human safety controls, and physical evidence state.
- `promote_external()` — additionally requires physical validation, an external replication reference, and external evidence state.
- `dry_run_envelope()` — deliberately non-promotable example/test envelope.

`semcap.py`

- `SemcapMeasurements` — semantic-edge measurement bundle.
- `reduction` and `utility_retention` — independent derived metrics.
- `evaluate_thresholds(...)` — evaluates declared experiment thresholds without representing them as certification or program criteria.
