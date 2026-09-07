# Actual Worldshepherd Host — PVK v0.5 Execution Handoff

**Purpose:** bind the current Git-controlled PVK candidate to the physical Worldshepherd host without replacing the historically verified `127.0.0.1:9530` service.

## Safety boundary

- Do **not** stop or overwrite the existing `9530` deployment merely to perform this acceptance run.
- Do **not** print `.env`, bearer tokens, or private rendered Compose configuration into chat, issue comments, or public evidence.
- Execute the candidate as a separate shadow Compose project on loopback port `19530` by default.
- The run proves bounded software/runtime behavior only. It does not validate any physical-science concept.

## 1. Baseline the existing local service

On the Worldshepherd host:

```bash
curl --fail --silent --show-error http://127.0.0.1:9530/health > /tmp/ws-sara-health-before.json
sha256sum /tmp/ws-sara-health-before.json
```

If the historical service is intentionally not running, record that fact rather than starting/stopping unrelated services solely for this step.

## 2. Use a separate validation checkout

Prefer a separate clone/worktree so the historical deployment directory is not mutated.

Example using a fresh directory:

```bash
mkdir -p "$HOME/worldshepherd-host-validation"
cd "$HOME/worldshepherd-host-validation"

git clone https://github.com/Bdavis1390/Sara_pro.git Sara_pro-pvk
cd Sara_pro-pvk
git fetch origin
git checkout worldshepherd/pvk-v0.5-cross-project-20260906
git pull --ff-only origin worldshepherd/pvk-v0.5-cross-project-20260906

git status --short
git rev-parse HEAD
```

Expected before execution: no tracked modifications.

If the repository requires an authenticated remote on the host, use the host's already-approved Git credential path. Do not paste a token into shell history.

## 3. Provide runtime secrets locally

The validation deployment requires the same SARA runtime-variable names used by the application. Create/copy `.env` locally without displaying its contents. If an existing approved `.env` is being reused, copy it with restrictive permissions rather than printing it:

```bash
cd deployments/sara_verified_local_v1
install -m 600 /PATH/TO/APPROVED/.env .env
```

Verify only presence/permissions:

```bash
stat -c '%a %n' .env
```

Expected mode: `600`.

## 4. Confirm the shadow port is free

```bash
python3 - <<'PY'
import socket
s = socket.socket()
try:
    s.bind(("127.0.0.1", 19530))
finally:
    s.close()
print("shadow_port_available=19530")
PY
```

If occupied, select another unused loopback port and export it before running:

```bash
export WS_PVK_SHADOW_PORT=19531
```

## 5. Execute the current-branch acceptance harness

Record the candidate commit immediately before execution:

```bash
candidate_commit="$(git rev-parse HEAD)"
printf 'candidate_commit=%s\n' "$candidate_commit"
```

Then execute:

```bash
bash scripts/verify_actual_host_pvk.sh
```

Do not use `sudo` unless the host's existing Docker configuration explicitly requires it; changing Docker privilege posture is outside this acceptance test.

A successful run ends with a message similar to:

```text
PASS: actual-host PVK shadow acceptance evidence: .host-pvk-evidence/<timestamp>
```

## 6. Verify the evidence manifest

```bash
latest="$(find .host-pvk-evidence -mindepth 1 -maxdepth 1 -type d | sort | tail -1)"
cat "$latest/RESULT.txt"
(
  cd "$latest"
  sha256sum -c SHA256SUMS
)
```

Required `RESULT.txt` values include:

```text
ACTUAL_HOST_PVK_SHADOW_ACCEPTANCE=PASS
relay_admin_boundary=PASS
pvk_record_append=PASS
pvk_claims_linter=PASS
pvk_restart_persistence=PASS
pvk_audit_presence=PASS
scientific_validation_claim=NOT_ESTABLISHED_BY_THIS_TEST
```

## 7. Run the independent machine evidence assessor

The repository contains a second verifier that independently checks the evidence manifest and acceptance relationships instead of trusting `RESULT.txt` alone.

From `deployments/sara_verified_local_v1`:

```bash
python3 scripts/assess_actual_host_pvk_evidence.py \
  "$latest" \
  --expected-branch worldshepherd/pvk-v0.5-cross-project-20260906 \
  --expected-commit "$candidate_commit"
```

Expected exit code: `0`.

Expected top-level output includes:

```json
{
  "accepted": true,
  "blockers": [],
  "scientific_validation_claim": "NOT_ESTABLISHED_BY_HOST_ACCEPTANCE"
}
```

The assessor independently verifies, among other checks:

- every required evidence object is present and included in `SHA256SUMS`;
- no hashed evidence file was modified after manifest creation;
- branch and commit agree between `baseline.txt`, `RESULT.txt`, and the expected command-line values;
- relay access to the PVK admin status path returned HTTP 403;
- the persistence probe remained at `concept` maturity and `IMPLEMENTED IN SOFTWARE` claim scope;
- the reactionless-propulsion linter test returned a `PROP-01` BLOCK;
- the same persistence-probe record is present after restart;
- required audit events are present.

Any blocker keeps host acceptance OPEN. Do not manually override an assessor failure by editing the evidence directory; rerun the controlled acceptance after resolving the cause.

## 8. Confirm the historical service was not disturbed

If it was running before the test:

```bash
curl --fail --silent --show-error http://127.0.0.1:9530/health > /tmp/ws-sara-health-after.json
sha256sum /tmp/ws-sara-health-after.json
```

The exact health JSON digest may change if runtime version/time-dependent fields differ; the acceptance criterion is that the historical service remains reachable on the intended loopback endpoint and its persistent state was not replaced by the shadow project.

## 9. Preserve, but do not publicly expose, the evidence

The evidence directory intentionally contains files marked `PRIVATE`, including potentially sensitive runtime configuration/audit information. Keep it owner-readable only and do not attach the full directory to a public GitHub issue.

Recommended next custody step:

1. create an encrypted/off-host copy through the existing Worldshepherd backup mechanism;
2. record only the evidence-directory identity, final SHA-256 manifest digest, branch, commit, timestamp, and PASS/FAIL state in the governance register;
3. retain the full private package for audit/review.

## 10. Acceptance interpretation

### PASS establishes

- this exact Git commit can build and run in a shadow deployment on the physical Worldshepherd host;
- the PVK authorization boundary behaves as tested;
- PVK record persistence survives the tested container restart;
- the claims linter blocks the selected unsupported reactionless-propulsion claim;
- required PVK/audit evidence exists for the run;
- the independently assessed evidence package has not been modified relative to its SHA-256 manifest.

### PASS does not establish

- abrupt-power-loss recovery;
- repeated host-reboot reliability;
- replacement-host restore unless separately tested;
- off-host backup adequacy;
- production security accreditation;
- material, RF, propulsion, energy, aerospace, sensing, or medical performance;
- scientific validity of any extraordinary physical mechanism.

Those remain separate evidence gates.
