# Worldshepherd Amazon Braket First Physical QPU Run — QRF-BELL-001

**Status:** operator-ready runbook; no AWS account, payment, reservation, or Worldshepherd QPU execution implied  
**Campaign gate:** `SARA-QRF-EXT-01`  
**Canonical workload:** `benchmarks/quantum/bell_qasm3.qasm`  
**Runtime:** Python 3.11+ using `requirements-quantum-braket.txt`

## 0. Claims boundary

This runbook is for obtaining **one governed physical-QPU result**. Account creation, Braket enablement, device discovery, payment, queue entry, or task creation is not mission evidence by itself.

A completed physical-QPU result can only begin the `single_external_hardware` evidence stage after:

1. the raw result is retained locally;
2. that exact raw artifact is SHA-256 hashed;
3. the generated evidence record passes structural ingest/current-gate checks;
4. an identified human performs technical review bound to the exact ingest decision; and
5. a separate canonical-state change is approved.

The first run cannot establish quantum advantage, cross-provider reproducibility, mission readiness, or deployment authority.

## 1. AWS account and Braket prerequisites

Amazon Braket must be enabled in the AWS account. The active user/role needs appropriate Braket permissions and S3 access. Third-party quantum computers require accepting the Braket third-party-device terms in the AWS console.

Official references:

- https://docs.aws.amazon.com/braket/latest/developerguide/braket-enable-overview.html
- https://docs.aws.amazon.com/braket/latest/developerguide/braket-manage-access.html

Do **not** place AWS access keys, secret keys, session tokens, passwords, SSO tokens, or account recovery material in Worldshepherd files, GitHub issues, chat, shell history, or evidence metadata.

### Preferred named-profile approach

If the AWS environment uses IAM Identity Center, AWS recommends the SSO token-provider configuration. Configure a named profile locally:

```bash
aws configure sso
aws sso login --profile <PROFILE_NAME>
aws sts get-caller-identity --profile <PROFILE_NAME>
```

Official reference:

- https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html

If an organization already supplies another secure AWS profile/role mechanism, use that instead. The QRF scripts accept the **profile name only**.

## 2. Create an isolated Braket runtime

Use Python 3.11 or newer because the current Amazon Braket Python SDK requires Python >=3.11.

```bash
cd <SARA_PRO_REPO>
python3.12 -m venv .venv-braket
source .venv-braket/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-quantum-braket.txt
```

Verify:

```bash
python -c 'import braket._sdk as sdk; print(sdk.__version__)'
```

Official SDK source/reference:

- https://github.com/amazon-braket/amazon-braket-sdk-python

## 3. Read-only device discovery — NO PAID TASK

Do not copy a device ARN from an old document. Query the active AWS account/region at execution time.

```bash
python scripts/list_braket_qpu_devices.py \
  --aws-profile <PROFILE_NAME> \
  --region <BRAKET_REGION> \
  --output .qrf-external/braket-qpu-discovery.json
```

The command performs only Amazon Braket `SearchDevices` and `GetDevice` operations. It filters for `deviceType=QPU` and `deviceStatus=ONLINE`, then displays:

- exact device ARN;
- provider and device name;
- current status;
- available queue information returned by the API;
- capability/snapshot digests.

The discovery artifact is **not hardware evidence**.

Official API references:

- https://docs.aws.amazon.com/braket/latest/APIReference/API_SearchDevices.html
- https://docs.aws.amazon.com/braket/latest/APIReference/API_GetDevice.html
- https://docs.aws.amazon.com/braket/latest/developerguide/braket-task-when.html

If no ONLINE QPU is returned, stop. Do not substitute a simulator to close the hardware gate.

## 4. Select the smallest scientifically suitable QPU route

For `QRF-BELL-001`, prioritize a gate-model QPU capable of the two-qubit Bell workload. Selection should consider:

- exact ONLINE state observed immediately before submission;
- current execution window/queue;
- provider modality desired for later independent reproduction;
- current official per-task/per-shot rate;
- whether the provider/device requires any additional terms or access configuration.

Record the exact ARN from the discovery output:

```bash
export WS_BRAKET_DEVICE_ARN='<EXACT_ONLINE_QPU_ARN_FROM_DISCOVERY>'
```

This is not a secret.

## 5. Re-check current pricing before submission

Current prices can change. Open the official pricing page immediately before the run:

- https://aws.amazon.com/braket/pricing/

Record the current:

- per-task USD rate;
- selected-device per-shot USD rate;
- intended shot count.

Calculate the predeclared estimate:

`estimated_cost = per_task_rate + shots * per_shot_rate`

The QRF runner stores this only as a **predeclared estimate**. Reconcile against actual AWS billing separately if needed.

## 6. S3 result destination

Use an existing authorized S3 bucket/prefix suitable for Braket task output. Do not put secrets in the bucket name or prefix.

```bash
export WS_BRAKET_S3_BUCKET='<AUTHORIZED_BUCKET_NAME>'
export WS_BRAKET_S3_PREFIX='worldshepherd/qrf-bell-001/<RUN_LABEL>'
```

## 7. Freeze the run configuration before seeing results

Before submission, record:

- exact Git commit SHA;
- canonical benchmark SHA-256;
- exact selected device ARN;
- AWS region/profile **name**;
- shots;
- pricing rates/source;
- S3 bucket/prefix;
- campaign gate `SARA-QRF-EXT-01`;
- UTC operator timestamp.

Do not alter thresholds, device selection, shot count, circuit semantics, or acceptance criteria after viewing the result merely to improve agreement.

## 8. Execute one physical QPU task

Example shape only—replace values with the current discovery/pricing data:

```bash
python scripts/run_braket_qpu_bell.py \
  --aws-profile <PROFILE_NAME> \
  --device-arn "$WS_BRAKET_DEVICE_ARN" \
  --s3-bucket "$WS_BRAKET_S3_BUCKET" \
  --s3-prefix "$WS_BRAKET_S3_PREFIX" \
  --shots 1024 \
  --per-task-usd <CURRENT_OFFICIAL_PER_TASK_RATE> \
  --per-shot-usd <CURRENT_OFFICIAL_DEVICE_PER_SHOT_RATE> \
  --pricing-source 'https://aws.amazon.com/braket/pricing/' \
  --project-id SARA-QRF \
  --campaign-gate-id SARA-QRF-EXT-01 \
  --output-dir .qrf-external/braket-qrf-bell-001/<RUN_LABEL>
```

The runner must reject simulator ARNs and must fail if the executed device ARN differs from the frozen requested ARN.

## 9. Expected local outputs

After a successful completed task:

- `braket_qrf_bell_001_raw_task.json`
- `braket_qrf_bell_001_task_record.json`
- `braket_qrf_bell_001_external_evidence.json`

The raw file contains provider task metadata and sampled results. The runner hashes that exact file before constructing the task/evidence records.

Preserve the raw artifact even if the Bell distribution is unexpectedly poor, anomalous, incomplete, or outside the predeclared reproduction thresholds.

## 10. Governed ingest — still NO automatic score promotion

Run the existing external-evidence ingest path against the retained artifact/package according to the QRF external-ingest contract. Structural acceptance means **ready for technical review only**.

An identified human reviewer must evaluate:

- actual physical-device provenance;
- canonical workload fidelity / provider compilation interpretation;
- result distribution and shot validity;
- device/configuration/calibration context available at run time;
- uncertainty/noise limitations;
- negative/anomalous evidence;
- pricing/timing distinction between estimate and observed metadata;
- conflict-of-interest / provider bias;
- claims-control compliance.

Only after a separate approved state-change action may the campaign consider promotion from integrated simulation toward the single-external-hardware evidence cap.

## 11. Repeat and independent-provider sequence

Do not stop at one successful-looking task.

1. Same provider/backend: perform a genuinely independent repeat with a distinct result artifact/run identity.
2. Second provider/modality: execute the same frozen canonical workload through IBM, IonQ, QSCOUT, QCUP/AQT, or another scientifically comparable real gate-model route.
3. Use the predeclared statistical reproduction policy (including TVD and Bhattacharyya-fidelity thresholds) rather than identical sampled-result hashes.
4. Retain failed reproduction as evidence.

## 12. Abort conditions

Stop rather than submit if:

- the selected device is not currently ONLINE;
- the ARN is not a QPU ARN;
- AWS profile/permissions are uncertain;
- third-party-device terms are not enabled where required;
- the current price has not been checked;
- the estimated cost exceeds the operator-approved budget;
- the S3 destination is not authorized;
- the benchmark or campaign-gate identity has changed unexpectedly;
- any step would require placing credential material in chat, source control, or evidence files.

A safe aborted run is preferable to an ambiguous or poorly governed hardware result.
