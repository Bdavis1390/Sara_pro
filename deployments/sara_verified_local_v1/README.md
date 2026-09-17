# Worldshepherd SARA / SSPADAWANZZ

Evidence-governed local administration, relay-recording, and predictive-requirements qualification service for the Worldshepherd stack.

## Verified boundary

- Local interface: `http://127.0.0.1:9530/ui` by default
- Set `SARA_HOST_PORT` to select another localhost-only publication port while retaining internal container port `9530`
- Unauthenticated compatibility health check: `/health`
- Liveness check: `/livez`
- Persistent-storage readiness check: `/readyz`
- Authenticated local relay record: `/v1/relay`
- Administrator audit: `/v1/audit?limit=50`
- Administrator registry: `/admin/registry`
- Administrator self-test: `/admin/selftest`

External scanning, broadcasting, arbitrary command execution, third-party activation, and self-expanding network behavior are excluded.

The audit is an application-appended JSON Lines log on the local persistent volume. It is useful operational evidence, but it is not immutable, tamper-proof, or independently verified.

## Quick start — SARA local service

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
# Replace both tokens with different random values.
./scripts/start_interface.sh
```

For the Docker-based acceptance sequence, see [`docs/VERIFIED_DEPLOYMENT.md`](docs/VERIFIED_DEPLOYMENT.md).

## Quick start — PRE full-bloom qualification compiler

After installing the package, compile the current frozen internal qualification evidence with:

```bash
rm -rf qualification_evidence
ws-pre-bloom \
  --fixtures fixtures \
  --out qualification_evidence \
  --software-commit "$(git rev-parse HEAD)" \
  --executed-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --operator "$(whoami)"
```

The compiler exits nonzero if a qualification record fails or ECHO-style custody verification fails. Expected outputs include `qualification_index.json`, domain qualification bundles, `capability_readiness_ledger.json`, `capability_horizons.json`, `software_provenance.json`, and the local hash-addressed `echo_store/`.

See [`docs/PRE_FULL_BLOOM.md`](docs/PRE_FULL_BLOOM.md) for operation and evidence interpretation, and [`docs/COMPLIANCE_BOUNDARY.md`](docs/COMPLIANCE_BOUNDARY.md) for the exact distinction between internal software conformance and external regulatory, contractual, physical, partner, and government validation.

## Quick start — HMAA Lattice Sandbox read-only validation

`ws-hmaa-sandbox-session` is zero-network by default. A preflight can be produced without connecting to Lattice:

```bash
ws-hmaa-sandbox-session \
  --mission-id WS-HMAA-SANDBOX-001 \
  --out hmaa-preflight
```

An external read is possible only after an authorized Lattice Sandboxes endpoint and credentials have been provided through environment variables. The command requires explicit network and authorization flags and a new evidence directory:

```bash
export LATTICE_ENDPOINT='<environment-id>.env.sandboxes.developer.anduril.com'
export SANDBOXES_TOKEN='<sandbox-account-token>'
export LATTICE_CLIENT_ID='<client-id>'
export LATTICE_CLIENT_SECRET='<client-secret>'

ws-hmaa-sandbox-session \
  --mission-id WS-HMAA-SANDBOX-001 \
  --execute-network \
  --authorization-confirmed \
  --capture-attempts 3 \
  --out hmaa-authorized-session-001
```

The runner is confined to the existing read-only Sandbox transport. It may acquire an OAuth token and read only the documented entity/task SSE streams; it does not expose entity publication, task mutation, agent execution, manual control, flight control, weapons actions, arbitrary hosts, or arbitrary paths.

A successful session still records `live_environment_validated=false`, `partner_validated=false`, `flight_validated=false`, and `operationally_validated=false`. Three attempts qualify for a partner-request package only when they produce at least three **distinct** fully `ALLOW` capture hashes.

See [`WS_HMAA_V1_2_AUTHORIZED_READ_SESSION_BOUNDARY.md`](WS_HMAA_V1_2_AUTHORIZED_READ_SESSION_BOUNDARY.md) for the executable claims/control boundary and [`docs/ANDURIL_LATTICE_READONLY_VALIDATION_BRIEF.md`](docs/ANDURIL_LATTICE_READONLY_VALIDATION_BRIEF.md) for the non-confidential partner review protocol.
