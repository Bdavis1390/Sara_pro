# Verified local deployment

## Deployment boundary

This release is a local administration, audit, registry, relay-recording, and PRE qualification service. The relay endpoint records approved local actions; it does not scan networks, broadcast to third parties, awaken external agents, or execute arbitrary commands.

The service binds to `127.0.0.1:${SARA_HOST_PORT:-9530}` through Docker Compose while retaining internal container port `9530`. Do not expose it publicly without a separate reverse proxy, TLS, identity provider, threat model, security review, and authorization.

## First deployment

```bash
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(32))'
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Put different generated values into SARA_RELAY_TOKEN and SARA_ADMIN_TOKEN.
./scripts/verify_deployment.sh
```

Open `http://127.0.0.1:<SARA_HOST_PORT>/ui` after the verification script passes. The default host port is `9530`.

## Required acceptance evidence

A promoted local deployment is internally verified only when all of the following are bound to the tested committed revision:

1. Python compilation and the complete unit/API suite pass.
2. The PRE full-bloom qualification compiler exits zero and required machine-readable outputs are retained.
3. ECHO-style custody verification passes for the compiled qualification bundles.
4. Docker Compose renders successfully and the container image builds.
5. Compatibility health, liveness, persistent-storage readiness, and UI checks pass.
6. Relay authorization works and relay credentials are denied administrator access.
7. Registry changes and audit records persist after restart.
8. The administrator self-test passes.
9. The verifier emits `tracked-files.json` from every Git-tracked file in this deployment subtree and records its canonical `tracked_files_sha256` together with `git_head` in `baseline.txt`.
10. Deployment logs, rendered/redacted Compose evidence, and SHA-256 evidence checksums are retained.
11. The corresponding GitHub Actions gate passes for the committed revision before it is called internally release-ready.

The rendered Compose evidence replaces the resolved `SARA_ADMIN_TOKEN` and `SARA_RELAY_TOKEN` values with `<REDACTED>` while preserving valid YAML. Evidence checksums are generated only after that redacted file is in place.

`MANIFEST.json` is deployment metadata and claims-boundary documentation. The historical July 2026 static file-hash list is superseded. The operative integrity inventory is generated at verification time from the tested Git-tracked subtree, preventing later expansion of the package from silently inheriting stale file hashes.

The audit is an application-appended local log. The service account can write it, so this deployment does not claim immutability, tamper-proof retention, or independent verification of the log or of external dispatch controls.

## Claims boundary

A successful local verifier and CI gate establish only the tested internal software/deployment behavior. They do not establish CMMC certification, organizational NIST SP 800-171 conformity, SPRS status, SAM/UEI/CAGE status, SBIR/STTR eligibility, ITAR/EAR compliance, FOCI determination, security clearance, ATO/RMF authorization, government interoperability certification, physical hardware performance, material qualification, RF performance, or operational effectiveness. See `COMPLIANCE_BOUNDARY.md`.

## Rollback

The application supports configuration/service rollback evidence in bounded internal tests, but full deployment rollback to a previous approved Git/container release has not yet been independently exercised as a production recovery demonstration. The commands below remain an operator procedure:

```bash
docker compose down
git checkout <previous-approved-commit>
docker compose up -d --build
```

The named Docker volume is not deleted by `docker compose down`. Do not use `-v` during an operational rollback unless destruction of local evidence is explicitly approved.

Replacement-host recovery and production/public-network readiness remain separate gates and require separately retained backups, a tested restore exercise, operational monitoring, identity/TLS architecture, threat modeling, and explicit authorization.
