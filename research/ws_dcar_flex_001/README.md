# WS-DCAR-FLEX-001

**Status:** `REFERENCE SOFTWARE + SYNTHETIC ADVERSARIAL TEST + EXTERNAL-SURROGATE ADAPTER + PARTNER-EVIDENCE CONTRACT / REQUIRES PARTNER VALIDATION`

Reference experiment for **Worldshepherd Data Center Assurance & Resilience (WS-DCAR)**.

## Purpose

Test a narrow assurance question:

> Given a data-center flexibility request, can an evidence verifier distinguish a genuinely compliant event from one that merely appears compliant at the utility boundary?

The reference model separates:

- requested versus measured grid reduction;
- mechanism decomposition (compute, migration, battery, on-site generation, HVAC);
- response latency and duration;
- authorization from evidence that authorization is actually known;
- source identity and request provenance;
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

## EXT-001 external-surrogate gate

`external_surrogate.py` adds the first external-format ingestion path without relaxing the evidence rules.

The first declared source is the public `pscad_load_short.csv` trace in `bram-exe/PSCAD-Hypersim-Data-Center-Modeling`, Git blob `693cb03b53af4d6fdeee72c88269c0e5dd0a48e9`. Its upstream measured GPU telemetry is attributed to the National Laboratory of the Rockies dataset DOI `10.7799/3025227`. The public PSCAD trace is a transformed load-deviation surrogate: its source script sums GPU telemetry, removes the mean, scales the variation to a nominal 250 MW data-center load, and expresses the result per-unit on a 5 GW system base.

EXT-001 therefore treats that trace as **external processed surrogate evidence**, not as an authoritative grid-boundary measurement. The adapter:

1. verifies the supplied text against the expected Git blob identity;
2. preserves a SHA-256 of the supplied external source;
3. records source repository, path, ref, upstream DOI, scaling bases, and transformation formula;
4. maps `dP_pu` to load using `grid_import_mw = data_center_base_mw + dP_pu * system_base_mw`;
5. marks grid-meter provenance as invalid because the source is a modeled/scaled load trace rather than a utility meter;
6. marks request provenance, authorization provenance, field-baseline validity, clock provenance, and configuration custody as unestablished;
7. consequently requires the verifier to return `INSUFFICIENT_EVIDENCE` rather than silently promoting a plausible power trace into a field-validation claim.

That fail-closed result is intentional. It demonstrates that WS-DCAR can ingest useful third-party power data while preserving the distinction between **external data** and **sufficient evidence of a specific authorized flexibility event**.

## Partner-evidence contract

`partner_bundle.py` defines the next-stage intake boundary for NLR-001 and ANL-001. A partner event declares its source organization/project, measurement boundary, request ID, authorization record, clock source, baseline method, configuration identity, meter identity, transformation history, and known limitations.

The builder is intentionally fail-closed:

- missing source/project identity invalidates source custody;
- missing request or authorization evidence cannot be inferred from the trace;
- a declared configuration ID must match every trace point;
- a declared meter ID must match every trace point and cannot override bad meter provenance;
- a lower-level boundary such as `cluster` remains `cluster_only`; it is never promoted into a facility or grid claim;
- a known unauthorized action is `NONCOMPLIANT`, whereas missing authorization evidence is `INSUFFICIENT_EVIDENCE`.

The staged external-validation protocol is documented in `docs/WS_DCAR_NLR_ARGONNE_VALIDATION_PROTOCOL_2026-09-30.md`: NLR first to extend the measured-workload lineage into a bounded partner-origin event, then Argonne JLSE for a controlled flexibility sweep with power/QoS context.

## Adversarial cases

The regression suite injects, among other cases:

1. incomplete evidence;
2. stale telemetry;
3. clock desynchronization;
4. invalid baseline;
5. invalid meter provenance;
6. configuration-custody failure;
7. unauthorized control;
8. missing authorization evidence;
9. missing request provenance;
10. missing source/project identity;
11. declared configuration identity mismatch;
12. declared meter identity mismatch;
13. measurement-boundary scope preservation;
14. grid-limit violation;
15. response-deadline miss;
16. duration shortfall;
17. generator substitution;
18. material rebound;
19. mechanism decomposition mismatch;
20. invalid negative measurement;
21. reduction-target mismatch independent of the absolute grid cap;
22. configuration drift within a time-series event;
23. meter-identity change;
24. excessive telemetry gap;
25. time-series late response;
26. time-series duration shortfall;
27. time-integrated energy decomposition mismatch;
28. replay provenance preservation;
29. replay-hash mutation detection;
30. external-source Git-blob mismatch;
31. external per-unit-to-MW transformation;
32. fail-closed external-surrogate disposition;
33. external source/transformation provenance preservation.

## Run

```bash
cd research/ws_dcar_flex_001
python -m pytest -q
```

A dedicated GitHub Actions workflow, `.github/workflows/ws-dcar-flex-001.yml`, compiles the reference implementation and runs the focused suite on relevant pull requests and pushes. External actions in that workflow are pinned to immutable commit SHAs under the repository's V23 no-regression policy.

## Claims boundary

Passing the synthetic, external-surrogate, and partner-evidence-contract suites is **not** evidence of MW-scale field performance, utility compliance, economic benefit, or grid-reliability improvement. Those remain `REQUIRES PARTNER VALIDATION`.

The experiment is an internal reference implementation of the Worldshepherd rule:

**command != evidence**

and the assurance chain:

**request -> authorization -> execution -> measurement -> provenance -> adversarial verification -> disposition**

## Next validation gate

The remaining controlling gate is a partner-origin or partner-controlled event bundle that combines the fields that the public surrogate cannot establish:

- actual measurement at the declared boundary, with authoritative meter identity;
- the issued request and request ID;
- authorization evidence;
- synchronized clock provenance;
- baseline definition and uncertainty;
- configuration identity/custody;
- mechanism telemetry where available;
- at least one adverse or exception case.

NLR-001 is the active first target. ANL-001 (Argonne JLSE) is queued immediately after it. Utility/grid claims remain blocked unless the event includes authoritative facility/grid-boundary evidence; node/cluster validation remains node/cluster validation.
