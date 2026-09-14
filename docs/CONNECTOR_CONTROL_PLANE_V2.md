# Worldshepherd Connector Control Plane v2

## Purpose

This layer governs how Worldshepherd proposes use of local tools and external connectors. It does not execute external actions by itself.

The control path is:

1. SARA proposes an action.
2. PRIME-style policy evaluates connector, action, actor role, data class, and approval state.
3. External writes remain denied until the required human approval state is present.
4. An allowed proposal receives an ECHO action envelope containing a SHA-256 provenance digest.
5. OVERWATCH-style health reporting summarizes connector inventory and policy posture.

## Governing rules

- Default deny.
- Unknown connectors are denied.
- Actions not present in a connector allow-list are denied.
- Actor roles are checked per connector.
- Data-class ceilings are enforced.
- Credential material is outside this policy module and must not be placed in the connector manifest.
- External writes require human approval by default.
- Policy authorization is not the same thing as execution.
- Capability or maturity claims are not upgraded by connector availability.

## Files

- `data/worldshepherd_connectors.v2.json` — connector/tool catalog and governance policy.
- `worldshepherd_sara/connector_control.py` — default-deny policy engine and ECHO envelope generation.
- `tools/connector_control/validate.py` — manifest and health validation.
- `tools/connector_control/evaluate.py` — dry-run policy evaluation only.
- `tests/test_connector_control.py` — policy regression tests.
- `.github/workflows/connector-control-ci.yml` — automated compile, validation, and default-deny checks.

## Local validation

```bash
python -m compileall worldshepherd_sara tools/connector_control
python tools/connector_control/validate.py
python -m pytest -q tests/test_connector_control.py
```

Expected policy behavior can also be inspected without performing an action:

```bash
python tools/connector_control/evaluate.py github repo.read --actor admin --data-class PUBLIC
```

An external write without approval must remain denied:

```bash
python tools/connector_control/evaluate.py github file.update --actor admin --data-class INTERNAL
```

The second command is expected to exit with status `2` because approval is absent.

## Integration boundary

The connector module intentionally contains no external service credentials and no direct API clients. Existing SARA authentication and audit boundaries should remain the front door when the control plane is mounted into the live gateway.

Do not add a second authentication implementation merely to expose these functions over HTTP. The preferred next integration is to call this policy engine from the already-authenticated SARA gateway and record only minimal policy/audit metadata.

## Connector maturity states

`enabled` means a local Worldshepherd control capability is available.

`external_connection` means the catalog expects a configured external connector, but this manifest alone does not prove the local runtime is connected.

`connection_optional` means the integration is useful but is not required for the core SARA control path.

These states describe integration posture, not technical readiness level of any Worldshepherd research program.

## Promotion gate

Before merging this branch into the active admin branch or `main`:

1. Connector CI must pass.
2. The branch delta must contain no credential material.
3. Existing SARA admin/operator separation must remain intact.
4. No connector may gain an external write action without an explicit policy entry.
5. A live gateway mount must reuse existing authentication rather than creating a parallel credential path.
