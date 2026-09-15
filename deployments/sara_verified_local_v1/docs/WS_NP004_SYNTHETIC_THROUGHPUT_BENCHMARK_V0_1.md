# WS NP004 Synthetic Throughput Benchmark v0.1

Status: DRAFT / SIMULATED_ONLY / INTERNAL SOFTWARE-PATH MEASUREMENT

This benchmark measures a bounded in-process software path over synthetic source updates. It covers the published Phase I planning envelope of 3, 5, and 8 simultaneous sources at 1, 5, and 10 Hz. The default profile runs each source/rate combination for 30 seconds.

## Measurement boundary

The timed initial-awareness path is limited to payload validation followed by generation of the informational alert and any initial informational recommendation. A second measurement records full synthetic replay and evidence-chain construction.

Excluded from the timing claim are external transport, message buses, UI rendering, display scan-out, operator response, real ASPN/pntOS/GPNTS adapters, physical sensors, and target shipboard hardware.

Therefore a measured value below one second is **not** evidence that the Navy end-to-end sub-second requirement has been satisfied. It is only an internal software-path observation on the recorded CI environment.

## Workload

The full default matrix is:

- source counts: 3, 5, 8
- source update rates: 1 Hz, 5 Hz, 10 Hz
- duration per case: 30 seconds
- cases: 9
- total synthetic source updates: 7,680

The generated workload is deterministic and receives a SHA-256 digest. Synthetic integrity-state transitions exercise nominal, degraded, suspect, disagreement, recovering, and restored states. These labels are test inputs; they are not evidence that Worldshepherd detects or classifies real-world APNT threats.

## Metrics

For every case, the artifact records:

- event count and recommendation count;
- p50, p95, p99, and maximum initial-awareness software-path latency;
- full replay elapsed time and events/second;
- evidence-trace completeness;
- whether the POC crossed its informational-only boundary;
- final synthetic integrity state;
- runtime and GitHub Actions environment metadata.

Percentiles use nearest-rank and timing uses `time.perf_counter_ns()`.

## Claims custody

Permitted after a successful exact-head run:

> Internally measured on a synthetic in-process workload covering 3–8 sources at 1–10 Hz; exact CI environment and timing artifact retained.

Not permitted without additional evidence:

- compliant with the Navy end-to-end sub-second latency requirement;
- validated on GPNTS or shipboard hardware;
- compatible with a particular ASPN or pntOS version;
- detects jamming or spoofing;
- improves operator effectiveness;
- Navy or Government validated.

The existing POC-A informational-only boundary remains unchanged.