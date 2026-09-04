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

## Astra solver profile

`Astra` is a Worldshepherd solver codename/profile, not a provider model identifier.

The current verified default OpenAI runtime target is `gpt-5.6-sol`, while model inference remains disabled by default. The implementation is in `worldshepherd_sara/astra_solver.py` and requires both an injected provider transport and explicit SARA model-inference authorization before a call can occur.

Fail-closed defaults:

- `SARA_ASTRA_MODEL=gpt-5.6-sol`
- `SARA_ASTRA_NETWORK_ENABLED=false`
- tool allowlist empty
- remote response storage disabled
- no embedded provider credentials
- no maturity upgrade from model output alone

See [`../../docs/ASTRA_INTEGRATION.md`](../../docs/ASTRA_INTEGRATION.md) for the architecture and promotion gates.
