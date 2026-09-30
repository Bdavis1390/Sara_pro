# WS-DCAR-FLEX-001

**Status:** `SIMULATED ONLY / REQUIRES PARTNER VALIDATION`

Synthetic reference experiment for **Worldshepherd Data Center Assurance & Resilience (WS-DCAR)**.

## Purpose

Test a narrow assurance question:

> Given a data-center flexibility request, can an evidence verifier distinguish a genuinely compliant event from one that merely appears compliant at the utility boundary?

The reference model separates:

- requested versus measured grid reduction;
- mechanism decomposition (compute, migration, battery, on-site generation, HVAC);
- response latency and duration;
- authorization;
- baseline validity;
- telemetry freshness and gap detection;
- meter provenance and meter identity;
- clock synchronization;
- configuration custody and configuration drift;
- rebound energy;
- integrated grid-energy reduction versus decomposed mechanism energy;
- deterministic replay-input and trace hashing for evidence custody.

## Canonical scenario

- baseline: 100 MW
- requested reduction: 20 MW
- grid-import ceiling: 80 MW
- response deadline: 300 s
- required duration: 1,800 s
- workload pause: 8 MW
- workload migration: 4 MW
- battery discharge: 5 MW
- HVAC reduction: 3 MW

The clean event verifies only when evidence and authorization gates also pass.

## Time-series replay

`fixtures/flex_001_trace.json` is a representative synthetic trace. `trace.py` verifies continuous evidence and contract behavior across the trace rather than trusting a single aggregate observation. The fixture explicitly records its synthetic provenance and transformation history. `replay.py` emits SHA-256 identifiers for the complete replay input and the point trace so a changed fixture cannot silently retain the same evidence identity.

Replay it with:

```bash
cd research/ws_dcar_flex_001
python replay.py fixtures/flex_001_trace.json
```

The replay reports the disposition, response latency, maintained duration, grid-energy reduction, decomposed energy, energy mismatch, minimum grid import, sample count, provenance object, input hash, and trace hash.

## Adversarial cases

The regression suite injects, among other cases:

1. incomplete evidence;
2. stale telemetry;
3. clock desynchronization;
4. invalid baseline;
5. invalid meter provenance;
6. configuration-custody failure;
7. unauthorized control;
8. grid-limit violation;
9. response-deadline miss;
10. duration shortfall;
11. generator substitution;
12. material rebound;
13. mechanism decomposition mismatch;
14. invalid negative measurement;
15. reduction-target mismatch independent of the absolute grid cap;
16. configuration drift within a time-series event;
17. meter-identity change;
18. excessive telemetry gap;
19. time-series late response;
20. time-series duration shortfall;
21. time-integrated energy decomposition mismatch;
22. replay provenance preservation;
23. replay-hash mutation detection.

## Run

```bash
cd research/ws_dcar_flex_001
python -m pytest -q
```

A dedicated GitHub Actions workflow, `.github/workflows/ws-dcar-flex-001.yml`, compiles the reference implementation and runs this suite on relevant pull requests and pushes. External actions in that workflow are pinned to immutable commit SHAs under the repository's V23 no-regression policy.

## Current internal evidence

Exact-head pull-request CI at branch head `ce72b6bbf90d7dfc31a3505041e6bffdb26fdcfa` completed successfully. The focused WS-DCAR gate reported:

```text
28 passed in 0.06s
```

The repository's Required Test and Build, CodeQL Required Gate, Repository Freshness Gate, SARA NIST 800-171 SSP Precursor, SARA Commit Closure Evidence, SARA Operational Resilience Drill, and V23 Action Pin No-Regression gates also completed successfully for the same head. These are internal software-evidence results only; partner validation remains independently controlling.

## Claims boundary

Passing this synthetic suite is **not** evidence of MW-scale field performance, utility compliance, economic benefit, or grid-reliability improvement. Those remain `REQUIRES PARTNER VALIDATION`.

The experiment is an internal reference implementation of the Worldshepherd rule:

**command != evidence**

and the assurance chain:

**request -> authorization -> execution -> measurement -> provenance -> adversarial verification -> disposition**
