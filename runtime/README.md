# Canonical SARA Runtime

**Status:** `CANONICAL`

**Claim state:** `IMPLEMENTED IN SOFTWARE` with evidence-gated internal verification

**Runtime package:** [`deployments/sara_verified_local_v1/`](../deployments/sara_verified_local_v1/)

This directory is the stable repository-level entry point for the runnable Worldshepherd SARA / SSPADAWANZZ local service. The implementation is intentionally **not duplicated** here: the canonical package remains under `deployments/sara_verified_local_v1/` so source, tests, deployment artifacts, evidence generation, and CI stay in one configuration-controlled location.

## Fastest local path

From the repository root:

```bash
bash scripts/sara.sh setup
bash scripts/sara.sh run
```

Then open:

```text
http://127.0.0.1:9530/ui
```

`setup` creates an isolated virtual environment inside the canonical runtime, installs the package and test dependencies using the committed CI constraints, and creates a mode-`0600` local `.env` with independently generated relay/admin bearer tokens if one does not already exist.

The setup command **does not overwrite an existing `.env`**.

## Operator commands

| Command | Purpose |
|---|---|
| `bash scripts/sara.sh setup` | Bootstrap the canonical local development/runtime environment |
| `bash scripts/sara.sh run` | Start the local SARA / SSPADAWANZZ interface |
| `bash scripts/sara.sh test` | Run the canonical runtime test suite |
| `bash scripts/sara.sh smoke` | Run the admin smoke test against an already-running local service |
| `bash scripts/sara.sh check` | Validate that the declared canonical package and required entry-point artifacts exist |
| `bash scripts/sara.sh path` | Print the canonical runtime path |

## Verified local interface

Default local endpoints include:

- `/health` — compatibility health check
- `/livez` — liveness
- `/readyz` — persistent-storage readiness
- `/ui` — local browser administration/status interface
- `/v1/relay` — authenticated **local relay-recording** endpoint
- `/v1/audit?limit=50` — administrator audit access
- `/admin/registry` — administrator registry operations
- `/admin/selftest` — administrator self-test

The current relay boundary is deliberately narrow: successful relay requests establish governed local recording/audit behavior. They do **not** establish third-party delivery, arbitrary command execution, external-network integration, broadcasting, scanning, or autonomous activation.

## Evidence and verification

The canonical runtime carries its own:

- installable `pyproject.toml`;
- pinned runtime and CI constraints;
- `.env.example` with placeholders only;
- unit/API tests under `tests/`;
- `scripts/start_interface.sh`;
- `scripts/admin_smoke_test.sh`;
- Docker/Compose deployment verification;
- recovery, rollback, resilience, release-evidence, SBOM and vulnerability-evidence paths;
- deployment manifest and detailed documentation.

The protected GitHub Actions gate is:

```text
.github/workflows/sara-verified-local-v1.yml
```

The historical-to-current SSPADAWANZZ differential is documented in:

```text
deployments/sara_verified_local_v1/docs/WS_QE_2026_ADM_001.md
```

That audit classifies the browser UI and admin audit endpoint as current implementations; credential separation, registry control, launcher and smoke test as strengthened implementations; and the old `integration_ok` wording as changed semantics because current relay behavior is explicitly `recorded_local_only`.

## Claims boundary

The repository may support narrow statements such as:

> The Verified Local SARA profile implements and tests a local governed administration, authorization, audit, registry and relay-recording service.

It does **not** by itself establish:

- field or flight readiness;
- partner or government validation;
- external-network integration;
- immutable or independently attested audit storage;
- CMMC certification;
- NIST 800-171 conformity or authorization;
- DFARS compliance;
- CUI authorization;
- classified-system approval;
- physical-system performance.

See [`../docs/CLAIMS_AND_EVIDENCE_POLICY.md`](../docs/CLAIMS_AND_EVIDENCE_POLICY.md) for repository-wide claim-state rules.

## Source of truth rule

If this entry-point document, the root README, or a wrapper command conflicts with the canonical runtime package, **the tested package and its protected CI evidence win**. Correct the stale entry-point documentation in the same change.
