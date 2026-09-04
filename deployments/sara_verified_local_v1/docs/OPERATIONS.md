# SARA Verified Local v1 — Operations & Incident Runbook

## Scope
This runbook applies to the localhost-only `sara_verified_local_v1` deployment and synthetic/public/releasable data. It does **not** authorize CUI, classified, export-controlled, partner-proprietary, or operational mission data and does not establish CMMC, NIST SP 800-171 compliance, RMF/ATO, or customer operational approval.

## Supported operating state
- Service must remain bound to loopback on the host unless a separately reviewed production profile is approved.
- The application container runs non-root, read-only root filesystem, dropped Linux capabilities, and `no-new-privileges`.
- Persistent application state resides in the named `sara_data` volume.
- Relay and admin credentials are separate; relay credentials must not authorize admin endpoints.
- `/livez` establishes process liveness. `/readyz` establishes application/storage readiness. `/health` is compatibility/status information, not an authorization decision.

## Operational checks
At start of shift or after deployment/recovery:
1. Run `docker compose config --quiet`.
2. Run `scripts/verify_deployment.sh`.
3. Confirm `/livez` and `/readyz` are healthy.
4. Confirm relay token remains blocked from admin endpoints.
5. Confirm audit append/self-test succeeds.
6. Capture `scripts/ops_snapshot.sh` output and retain with the relevant release/incident record.

## Incident classes
- **SEV-1:** suspected credential compromise, unauthorized admin action, integrity/custody failure, prohibited-data exposure, or inability to trust audit/configuration state.
- **SEV-2:** service unavailable, readiness failure, persistent-data corruption, repeated authorization failures, or recovery failure without evidence of compromise.
- **SEV-3:** degraded/non-critical function, performance regression, warning-level dependency/runtime issue, or documentation/configuration drift.

## Fail-closed response
For SEV-1:
1. Stop consequential automation and do not approve new external actions.
2. Preserve logs/evidence before destructive remediation when safe.
3. Rotate affected credentials outside version control.
4. Isolate the localhost deployment from any external integration path.
5. Record incident UTC start, operator, Git commit, configuration digest, evidence digests, observed symptoms, containment action, and recovery decision.
6. Restore only from an approved evidence-backed state; do not silently repair an untrusted history.
7. Require explicit human closure/re-authorization before resuming consequential workflows.

For SEV-2:
1. Capture operations snapshot and container logs.
2. Run readiness/self-test.
3. If persistent state is suspect, run the recovery procedure against a verified backup artifact.
4. Verify exact evidence/data inventory after restore.
5. Record discrepancy and root cause before returning to normal operation.

For SEV-3:
1. Record the regression/warning and affected version.
2. Open a tracked corrective issue.
3. Do not promote evidence maturity merely because the service remains available.

## Evidence retention baseline
The public CI evidence retention period is a convenience baseline, not a federal records schedule. For this local profile:
- Qualification and recovery artifacts should be retained for at least 90 days when CI storage permits.
- Release acceptance records should retain commit SHA, artifact SHA-256, workflow/run identity, and claims boundary even after ephemeral artifacts expire.
- Incidents remain open until evidence identifies containment, restoration state, residual risk, and authorized closure.
- Deletion or retention changes involving regulated/customer records require separate legal/contract review.

## Recovery
`scripts/recovery_exercise.sh` proves a destructive named-volume backup/restore loop for synthetic/public local data. It does **not** prove replacement-host recovery, off-host independent retention, disaster recovery across regions, or controlled-data restoration.

## Rollback
A rollback is authorized only to a specifically identified prior release whose code/evidence state is known. Rollback must preserve an immutable record of:
- source release commit;
- target prior commit/image;
- data/schema compatibility decision;
- pre-rollback backup digest;
- post-rollback readiness and smoke-test results;
- operator approval.

Until a CI rollback drill against a frozen prior release is green, full deployment rollback remains an open production-readiness gate.

## Escalation / claims rule
When uncertainty exists, classify the state as `UNVERIFIED` or the applicable `REQUIRES_*` category and escalate. No operational procedure may convert internal evidence into external certification, physical validation, government acceptance, or legal eligibility.

## Research intake governance reference
Worldshepherd Research Intake Wave 3 is governed by the repository-level intake record, claims matrix, machine-readable ledger, and execution queue under `../../../docs/WS_RESEARCH_INGEST_WAVE3_*`. These records are evidence-governance inputs only; they do not authorize external network activity, controlled-data handling, physical capability claims, partner validation, or operational use.