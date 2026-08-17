# Worldshepherd QRF — SARA First Real-QPU Runbook

**Date:** 2026-08-17  
**Gate:** `SARA-QRF-EXT-01`  
**Target transition:** `integrated_simulation` -> `single_external_hardware`

## Purpose

Execute `QRF-BELL-001` on one named IBM Quantum real-QPU backend and produce a structurally complete Worldshepherd external-evidence package without persisting the API key in source control.

This run closes only the first external-hardware acquisition gate if the resulting package passes structural intake and identified-human technical review. It does **not** establish quantum advantage, reproduced-hardware evidence, 97 mission readiness, or deployment authority.

## Current access basis

As checked on 2026-08-17, IBM Quantum Platform documents an **Open Plan** with free QPU access up to 10 minutes per rolling 28-day window. IBM also documents a limited-time 2026 opt-in promotion for active Open Plan users. Current Qiskit Runtime documentation uses the `ibm_quantum_platform` service path and API-key authentication.

IBM documents that Open Plan workloads can run in **job mode or batch mode**, but not Session mode. The Worldshepherd runner uses `SamplerV2(mode=backend)`, which IBM documents as job mode.

Re-verify access terms and client behavior immediately before execution because plans and APIs can change.

Official references:

- https://quantum.cloud.ibm.com/docs/en/guides/plans-overview
- https://quantum.cloud.ibm.com/docs/en/guides/instances
- https://quantum.cloud.ibm.com/docs/en/guides/run-jobs-session
- https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service
- https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/sampler-v2
- https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/runtime-job-v2

## Preconditions

1. A real IBM Quantum Platform account exists.
2. The account has an active instance/plan that permits real-QPU execution.
3. The intended plan is known. Use `open` only when the intended execution is on an Open Plan instance.
4. The API key is available to the operator at runtime.
5. The working tree is on the governed QRF branch/revision intended for the run.
6. `requirements-quantum.txt` installs successfully.
7. The API key is **never** pasted into source files, JSON evidence, issue comments, Git commits, terminal commands that would enter shell history, or chat.
8. No hardware job is submitted unless the runner can resolve the active IBM instance and its actual plan before submission.

## Local preparation

From the repository root:

```bash
python3 -m venv .venv-qrf
source .venv-qrf/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-quantum.txt
PYTHONPATH=. pytest -q tests/test_quantum_*.py tests/test_pqc_inventory.py
```

Do not continue to hardware if the governed test suite fails.

## Inject the API key without putting it in shell history

```bash
read -rsp "IBM Quantum API key: " IBM_QUANTUM_TOKEN
echo
export IBM_QUANTUM_TOKEN
```

For an intended Open Plan run:

```bash
export IBM_QUANTUM_PLAN_NAME=open
```

If a specific IBM instance/CRN is already known, bind the run to it:

```bash
read -rp "IBM Quantum instance/CRN: " IBM_QUANTUM_INSTANCE
export IBM_QUANTUM_INSTANCE
```

If no instance is supplied, the runner passes the expected plan as an IBM `plans_preference` constraint before backend selection. If an instance is supplied, the runner resolves that instance's actual plan through the service. In both cases the resolved plan must match `IBM_QUANTUM_PLAN_NAME` **before any QPU submission** or the run aborts.

If a paid plan is used, record the actual job cost rather than assuming zero:

```bash
export IBM_QUANTUM_PLAN_NAME='pay-as-you-go'
export IBM_QUANTUM_JOB_COST_USD='<actual recorded cost>'
```

For Open Plan, the runner may record `0.0` only after IBM resolves the actual execution instance as Open Plan.

## Execute

Allow the adapter to select an operational least-busy real backend within the verified plan/instance:

```bash
PYTHONPATH=. python scripts/run_ibm_qpu_bell.py \
  --output .qrf-artifacts/qrf_bell_001_ibm_qpu_evidence.json
```

Or pin a named real backend only after confirming that it is operational and available to the intended account/instance:

```bash
PYTHONPATH=. python scripts/run_ibm_qpu_bell.py \
  --backend '<actual-backend-name>' \
  --output .qrf-artifacts/qrf_bell_001_ibm_qpu_evidence.json
```

The script intentionally rejects simulator backends. It also refuses submission if the active instance or instance plan cannot be verified, or if the verified plan does not match the expected plan.

## What the runner retains

The governed bundle includes, when IBM exposes the relevant fields:

- provider identity
- service-resolved IBM instance identity
- service-resolved IBM instance plan
- named backend
- IBM job ID
- shot count and counts
- Bell correlated fraction
- source-circuit SHA-256
- transpiled/ISA-circuit SHA-256
- result SHA-256
- backend-properties SHA-256
- calibration/update identity where exposed
- backend qubit count and native operations
- Qiskit Runtime version
- IBM job metrics and metrics SHA-256
- measured queue time from IBM `created` -> `running` timestamps
- measured platform latency from IBM `created` -> `finished` timestamps
- independently measured local wall latency
- QPU charge/usage time where IBM exposes it
- recorded job cost
- `plan_verification=service_resolved_before_submission`
- `campaign_gate_id=SARA-QRF-EXT-01`

The adapter fails closed if the first-gate package cannot retain verified instance/plan identity, backend-properties identity, measured queue timing, or measured end-to-end latency.

## Validate the retained artifact

```bash
python -m json.tool .qrf-artifacts/qrf_bell_001_ibm_qpu_evidence.json >/dev/null
```

Inspect the gate result and actual IBM access identity:

```bash
python - <<'PY'
import json
p = '.qrf-artifacts/qrf_bell_001_ibm_qpu_evidence.json'
d = json.load(open(p, encoding='utf-8'))
print('instance:', d['hardware_result']['instance'])
print('plan:', d['hardware_result']['instance_plan'])
print('backend:', d['hardware_result']['backend'])
print('job_id:', d['hardware_result']['job_id'])
print('intake accepted:', d['intake_decision']['accepted_for_intake'])
print('achieved stage:', d['campaign_evaluation']['achieved_stage'])
print('next gate:', d['campaign_evaluation']['next_gate_id'])
PY
```

Expected structural outcome for a valid first real-QPU package:

```text
intake accepted: True
achieved stage: single_external_hardware
next gate: SARA-QRF-EXT-02
```

Anything else is **not** first-hardware closure. Even this expected structural outcome is only ready for technical review; it does not automatically mutate canonical mission state.

## Human technical review

After structural ingest, bind the human review to the exact ingest-decision digest using the QRF external-review contract. The generated review template defaults `promotion_recommended` to `false` and may not be treated as approval merely because an AI prepared it.

The identified human reviewer must explicitly assess technical validity, provenance, uncertainty/error treatment, negative/anomalous evidence, claims control, and bias/conflict considerations before recommending any state promotion.

## Credential cleanup

Immediately after the run:

```bash
unset IBM_QUANTUM_TOKEN
unset IBM_QUANTUM_INSTANCE
unset IBM_QUANTUM_PLAN_NAME
unset IBM_QUANTUM_JOB_COST_USD
```

Deactivate the environment when finished:

```bash
deactivate
```

## Evidence handling

Do not automatically commit the hardware evidence bundle. Review it first for account-specific identifiers, data-sharing restrictions, and any information that should remain in controlled evidence storage. The API key is not intentionally retained by the runner, but that does not remove the obligation to inspect the artifact before publication.

## Next gate

After one structurally accepted and human-reviewed real-QPU run, SARA may be considered for a **separate governed** promotion to `single_external_hardware`. `SARA-QRF-EXT-02` then requires a frozen replication series with at least two real-QPU execution records. A second run is not optional if the objective is reproduced-hardware evidence.
