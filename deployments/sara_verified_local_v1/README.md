# Worldshepherd SARA / SSPADAWANZZ

Evidence-governed local administration and relay-recording service for the Worldshepherd stack.

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

The audit is an application-appended JSON Lines log on the local persistent
volume. It is useful operational evidence, but it is not immutable,
tamper-proof, or independently verified.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
# Replace both tokens with different random values.
./scripts/start_interface.sh
```

For the Docker-based acceptance sequence, see [`docs/VERIFIED_DEPLOYMENT.md`](docs/VERIFIED_DEPLOYMENT.md).
