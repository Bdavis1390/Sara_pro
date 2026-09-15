# GD-04C — W-RMABM G2B Provenance Integrity, Disagreement, Clock-Skew & Scale Specification

**Status:** INTERNAL G2 INCREMENT / SYNTHETIC ONLY / REQUIRES EXTERNAL VALIDATION

## Purpose
Strengthen W-RMABM evidence beyond G1 digest-format checks and the first G2 fault campaign by testing actual source-byte integrity, loss of corroboration, temporal disagreement, and repeatable synthetic scale measurements.

## Added evidence
### 1. Bound source-byte provenance
Each synthetic observation can be paired with source bytes encoded in a manifest. The claimed SHA-256 is recomputed from those bytes before the mission-assurance thread runs. Any mismatch is rejected before fusion or advisory evaluation.

### 2. Source disagreement
A previously corroborating synthetic source is spatially displaced beyond the configured fusion boundary. The two-source authorization condition must disappear; remaining tracks are held rather than promoted.

### 3. Clock skew / staleness
A supporting source is shifted outside the configured freshness window. It must be retained in stale-source traceability but excluded from fusion, preventing two-source advisory authorization.

### 4. Synthetic scale measurement
A deterministic generator creates separated two-source clusters. The benchmark records observation count, decision count, authorized-advisory count, elapsed wall-clock time, audit hash, Python version, platform, and machine type.

No absolute latency threshold is asserted at this stage. Timing is environment-specific and must not be represented as operational missile-warning/tracking performance.

## Files
- `deployments/sara_verified_local_v1/worldshepherd_sara/rmabm_provenance.py`
- `deployments/sara_verified_local_v1/tests/test_rmabm_g2b.py`
- `deployments/sara_verified_local_v1/tools/rmabm_g2b_benchmark.py`

## Acceptance criteria
- Untampered bound source bytes verify and cover every observation.
- Modified source bytes with an unchanged claimed digest are rejected.
- Source disagreement removes the prior two-source authorization condition.
- Clock-skewed/stale corroborating sources cannot contribute to authorization.
- A 25-pair synthetic CI fixture produces 50 observations and 25 deterministic two-source decisions.
- Repeated scale fixtures produce the same audit hash even though elapsed wall-clock time may vary.
- Safety boundary remains advisory-only; no operational engagement logic is introduced.

## Remaining G2 gaps after this increment
- broader seeded Monte Carlo campaign across many seeds and combined faults;
- event duplication/reordering and replay-conflict handling beyond the existing deterministic replay tests;
- explicit throughput curves across several fixture sizes with retained CI artifacts;
- memory/CPU measurements and environment manifests suitable for independent reproduction;
- policy-ablation negative controls;
- provenance-enabled versus provenance-disabled overhead comparison;
- independent external rerun.

## Claims boundary
This increment can support only an internal claim of deterministic synthetic provenance/fault/scale behavior after clean CI. It does not establish operational missile-defense performance, BAE/SDA/SSC/Space Force/Golden Dome validation or integration, classified suitability, CMMC certification, NIST SP 800-171 conformity, or government acceptance.
