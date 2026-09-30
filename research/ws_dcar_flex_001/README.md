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
- telemetry freshness;
- meter provenance;
- clock synchronization;
- configuration custody;
- rebound energy.

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

## Adversarial cases

The regression suite injects:

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
15. reduction-target mismatch independent of the absolute grid cap.

## Run

```bash
cd research/ws_dcar_flex_001
python -m pytest -q
```

## Claims boundary

Passing this synthetic suite is **not** evidence of MW-scale field performance, utility compliance, economic benefit, or grid-reliability improvement. Those remain `REQUIRES PARTNER VALIDATION`.

The experiment is an internal reference implementation of the Worldshepherd rule:

**command != evidence**

and the assurance chain:

**request -> authorization -> execution -> measurement -> provenance -> adversarial verification -> disposition**
