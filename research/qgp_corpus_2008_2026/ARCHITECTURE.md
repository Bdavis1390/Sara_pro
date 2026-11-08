# WS-QGP-ARCH.2 — scalable research intake without Palace interference
Version 2.0 | 2026-11-08 | Draft implementation / branch isolated

## Purpose
Accommodate external QGP/QCD literature (2008–2026), derived numerical datasets, and future large detector-event collections using the existing WorldShepherd evidence-governance model.

## Observed infrastructure
- Lenovo online, Python 3.10, approximately 4.5 GiB free in /home and 1.1 GiB available RAM at the initial check.
- Other SARA and Palace recovery workloads exist; never terminate, restart, overwrite, or compete with them.
- GitHub Sara_pro dedicated branch for public code and CC0 public derived data.
- Current HEPData numerical tables are CC0 and copied byte-exact with SHA-256 validation.
- Oracle, Kaggle, rclone and aws CLIs were not found on Lenovo. No cloud compute or object storage upload is claimed.

## Tiered architecture
Tier 0: INSPIRE/OpenAlex metadata (small; SQLite WAL; read-only provider API).
Tier 1: HEPData public derived tables (small; exact source bytes; CC0; SHA-256; numerical unit tests).
Tier 2: Reproducible analysis artifacts (code, deterministic versions, input manifests, calibration and covariance assumptions, log files).
Tier 3: Large open raw events and container images (provider-origin URL and checksums only until externally approved storage and compute have been verified).

Source flows: public provider -> query/provenance log -> DOI/arXiv normalization -> source evidence registry -> SARA draft staging -> approved scientific analysis. No publication or original-claim escalation from metadata collection alone.

## Incremental workload behavior
- 22 topics by 19 years by 2 providers = 836 initial topic/year/provider partitions, subject to yearly and topical overlap. A partition is not an exhaustive publication count.
- Each topic uses independently checkpointed pages, query URL and raw HTTP SHA-256.
- One writer, SQLite transaction-per-page, default 40 records/page. All retries bounded.
- Default hard guards: max 12 requests, 120 seconds, at least 3 GiB free disk, max DB 128 MiB. Process runs at nice 19 for sampled deployments.
- Explicit --refresh required to revisit pages because result ordering can change. Source corrections and retractions need separate audit.
- Inspect work state before starting a new run. Never displace or reconfigure Palace.
- No authorization to bulk-download copyright-protected articles or raw detector files, overwrite scientific artifacts, deploy hazardous RF, or make external IP claims.

## SARA mapping
External publication records are SOURCE_INDEXED_UNREVIEWED. Keep physics_domain, model_scope, DOI, source URL, published date, uncertainty_method, raw_data_digest (null for metadata), validation_state, independent_review_state, and CRE1AWS approval pending.
HEPData derived tables are PUBLISHED_TABLE_DOWNLOADED_CHECKSUMMED; they are not STAR raw detector observations and do not establish independent reproduction. Store separate data-source and computed-output digests.

## Scientific validation gates
WS-QGP-THERMO-001: check source table hashes and units; then reconstruct thermal dielectron background subtraction, fit range and covariance before claiming a reproduction.
WS-QGP-BARYON-001: source rapidity and baryon/charge observations; compare explicit valence and junction model predictions with out-of-sample metrics.
WS-QGP-NONGAUSS-001: evaluate skewed and heavy-tailed transport models with held-out tests.
WS-RF-PAIR-001: frequency ratios are hypotheses, not evidence of QCD-scale microwave coupling. Calibrated bench controls and independent test required.
BAROS: transfer inverse-modeling methods only, not QGP mechanisms into clinical claims.

## Operating discipline
Keep exactly the existing three active scheduled task owners; no fourth task created. This branch does not modify those schedules. No automatic ingestion task has been installed. An approved future run must log exact commit, start/end time, source counts, storage footprints, process exit status, and limitations.

## Sources
INSPIRE: https://inspirehep.net/api/literature
OpenAlex: https://api.openalex.org/works
STAR HEPData: https://hepdata.net/record/147195?format=json
CERN Open Data: https://opendata.cern.ch
sPHENIX public: https://www.sphenix.bnl.gov/PublicResults

The user retains scientific and external release approval authority. This architecture is a bounded implementation, not a complete mirror of all 2008–2026 QGP science.
