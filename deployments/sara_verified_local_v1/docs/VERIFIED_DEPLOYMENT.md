# Verified local deployment

## Deployment boundary

This release is a local administration, audit, registry, and relay-recording service. The relay endpoint records approved local actions; it does not scan networks, broadcast to third parties, awaken external agents, or execute arbitrary commands.

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

A deployment is verified only when all of the following exist for the same Git commit:

1. CI unit and API tests pass.
2. The container image builds.
3. Health and UI checks pass.
4. Relay authorization works.
5. Relay credentials are denied administrator access.
6. Registry changes persist.
7. Audit records persist after restart.
8. The administrator self-test passes.
9. Deployment logs and evidence checksums are retained.
10. CRE1AWS reviews and approves the evidence package.

## Rollback

```bash
docker compose down
git checkout <previous-approved-commit>
docker compose up -d --build
```

The named Docker volume is not deleted by `docker compose down`. Do not use `-v` during an operational rollback unless destruction of local evidence is explicitly approved.
