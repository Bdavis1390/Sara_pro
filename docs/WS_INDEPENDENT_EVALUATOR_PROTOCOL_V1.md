# Worldshepherd Independent Evaluator Protocol v1

Status: PUBLIC / UNCLASSIFIED REPRODUCTION PROTOCOL

Purpose: allow an independent evaluator to reproduce the Worldshepherd governance/evidence proof without relying on claims from a Worldshepherd operator.

## Scope

This protocol evaluates only the current public software/governance wedge:
- evidence lineage;
- deterministic synthetic fusion;
- mission replay and traceability;
- bounded autonomy policy;
- identified-human approval/denial/revocation;
- visible DDIL conflict handling;
- deterministic higher-authority resolution;
- internal qualification evidence generation;
- bounded synthetic performance.

It does **not** evaluate or establish CUI/classified authorization, CMMC/SPRS, ATO/RMF, operational ISR performance, flight/weapon/sensor validation, government acceptance, or production deployment.

## Reference branch

Repository: `Bdavis1390/Sara_pro`

Branch: `worldshepherd-capture-engine-v1-1`

Canonical evidence index: `config/worldshepherd_selection_evidence_index_v1.json`

Current preferred-choice matrix: `config/worldshepherd_preferred_choice_matrix_v0_2.json`

## Evaluator independence rules

1. Use a clean checkout or ephemeral environment.
2. Do not accept pre-generated result files as proof of execution; generate fresh outputs.
3. Record exact git commit, host/runtime metadata, start/end timestamps, and any environment changes.
4. Do not change acceptance thresholds to obtain a passing result.
5. Preserve failures, warnings, and anomalous output.
6. Do not add controlled, proprietary, export-controlled, or classified data.
7. Do not infer physical-system or operational performance from the software demonstration.
8. If a result differs from the canonical result, report the difference before attempting remediation.

## Reproduction sequence

### A. Inspect claims boundaries

Read:
- `SECURITY.md`
- `config/worldshepherd_preferred_choice_matrix_v0_2.json`
- `config/worldshepherd_selection_evidence_index_v1.json`
- `config/worldshepherd_requirements_to_evidence_crosswalk_v0_1.json`
- `docs/WS_EVALUATOR_DEMONSTRATION_PACK_V1.md`

Pass condition: evaluator confirms that the package distinguishes internal software evidence from external compliance, operational, and physical-validation claims.

### B. Run integrated evaluator demonstration

Install the public SARA package in a clean Python 3.11 environment, then run:

```bash
mkdir -p evaluator_evidence
python tools/selection_demo/run_evaluator_demo.py \
  --out evaluator_evidence/worldshepherd-evaluator-demo-v1.json \
  --software-commit "$(git rev-parse HEAD)"
```

Expected semantic properties, not hard-coded output text:
- `result == PASS`
- `deterministic_rerun == true`
- every acceptance check is `true`
- one or more human decisions are present;
- `APPROVED`, `DENIED`, and `REVOKED` states are represented;
- explicitly denied action disposition is `DENIED`;
- equal-clock/equal-authority divergence is `CONFLICT` with no selected state;
- a later higher-authority human state resolves deterministically;
- every top-level demonstration claim contains evidence references.

The canonical internal semantic digest was:
`sha256:153a4e71793aaeebb6ded664c34c7aa378e59fc83783ee2067ba6756e0c745c0`

A different digest is not automatically a failure if the evaluator is on a later commit. It must be explained by the exact-commit/configuration delta.

### C. Run selection-core baseline

Execute:

```bash
chmod +x tools/selection_demo/run_selection_baseline.sh
WS_SELECTION_EVIDENCE_DIR="$PWD/selection_evidence" \
  tools/selection_demo/run_selection_baseline.sh
```

Expected outcome on the canonical internal evidence chain:
`BASELINE_PASS_WITH_UNRESOLVED_GATES`

The unresolved gates are expected to remain visible. A result that silently removes them is not equivalent evidence.

### D. Run bounded synthetic scale benchmark

Execute:

```bash
mkdir -p scale_evidence
python tools/selection_demo/benchmark_synthetic_fusion.py \
  --out scale_evidence/synthetic-fusion-scale-benchmark.json \
  --software-commit "$(git rev-parse HEAD)"
```

Evaluator records the measured host-specific values. Do not require them to equal the GitHub-hosted values because hardware/load vary. Required properties:
- deterministic output for each profile;
- exact host/runtime metadata retained;
- no reinterpretation as end-to-end DIU/ISR performance;
- reference targets remain labeled as reference targets only.

Canonical internal GitHub-hosted reference at 10,000 synthetic observations:
- serialized input ~1.10168 MB;
- p95 ~36.97 ms;
- function-only throughput ~1,787.97 MB/min.

These values are not procurement compliance thresholds.

### E. Inspect retained negative evidence

Review issue `#245` and the selection manifest.

Required evaluator conclusion: the NSB G10 MHD cross-helicity failure remains separately visible and is not reclassified as passing merely because it is outside the procurement-selection core.

Canonical observed negative result:
- cross-helicity relative drift ~`3.6710178210651096e-05`;
- frozen acceptance limit `2e-05`;
- capability status `SIMULATED_ONLY`.

### F. Record independent conclusion

Evaluator should answer each question `YES`, `NO`, or `INCONCLUSIVE` with evidence references:

1. Does the synthetic fusion output preserve source observation lineage?
2. Are mission findings/proposals traceable to source events?
3. Are high-authority actions kept behind identified-human review in the evaluator scenario?
4. Does an explicit denied action fail closed?
5. Can the evaluator observe approval, denial, and revocation as distinct states?
6. Does equal-priority DDIL divergence surface as a conflict instead of silent overwrite?
7. Does a later higher-authority human state resolve that synthetic conflict deterministically?
8. Does the evidence package preserve claims boundaries and known negative evidence?
9. Are the outputs reproducible from a clean environment at the tested commit?
10. Are any claims being made beyond what the evidence supports?

## Independent-evidence classification

If questions 1–9 are `YES` and question 10 is `NO`, classify:

`INDEPENDENTLY_REPRODUCED_GOVERNANCE_WEDGE`

Do not classify:
- `government approved`;
- `CMMC compliant`;
- `classified ready`;
- `operationally validated`;
- `preferred government vendor`;
- `superior to all competitors`.

Those require separate evidence.

## Selection interpretation

A successful independent reproduction would close the current internal-only limitation for the governance/evidence wedge and provide external validation that Worldshepherd's differentiator is observable rather than self-asserted.

It would still not close contract-specific cyber, clearance, licensing, or operational-scale requirements.
