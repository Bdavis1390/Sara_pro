from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from worldshepherd_sara.app import app
from worldshepherd_sara.fasa_readiness_recovery import (
    FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY,
)
from worldshepherd_sara.fasa_runtime_gate import (
    FASA_EXECUTION_READINESS_RECORD_SCHEMA,
    FASA_EXECUTION_READINESS_REGISTRY_KEY,
)
from worldshepherd_sara.storage import DurableStore


DIGEST = "c" * 64


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_service_startup_tombstones_expired_waiting_readiness(tokens):
    _relay, admin = tokens
    root = Path(os.environ["SARA_DATA_DIR"])
    store = DurableStore(root)
    store.patch_registry(
        {
            FASA_EXECUTION_READINESS_REGISTRY_KEY: {
                "T-STARTUP-EXPIRED": {
                    "schema": FASA_EXECUTION_READINESS_RECORD_SCHEMA,
                    "status": "WAITING_ECHO",
                    "transition_id": "T-STARTUP-EXPIRED",
                    "action_id": "ACTION-STARTUP-EXPIRED",
                    "authorization_id": "AUTH-STARTUP-EXPIRED",
                    "provenance_event_id": "EVENT-STARTUP-EXPIRED",
                    "decision_digest_sha256": DIGEST,
                    "created_at": "2000-01-01T00:00:00Z",
                    "expires_at": "2000-01-01T00:01:00Z",
                }
            }
        }
    )

    with TestClient(app) as client:
        registry_response = client.get("/admin/registry", headers=_auth(admin))
        assert registry_response.status_code == 200
        registry = registry_response.json()["registry"]
        assert "T-STARTUP-EXPIRED" not in registry[FASA_EXECUTION_READINESS_REGISTRY_KEY]
        tombstone = registry[FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY][
            "T-STARTUP-EXPIRED"
        ]
        assert tombstone["expired_from"] == "WAITING_ECHO"
        assert tombstone["authorization_id"] == "AUTH-STARTUP-EXPIRED"

        audit_response = client.get("/v1/audit?limit=50", headers=_auth(admin))
        assert audit_response.status_code == 200
        started = [
            record
            for record in audit_response.json()["records"]
            if record["event"] == "service_started"
        ]
        assert started
        recovery = started[-1]["payload"]["fasa_readiness_recovery"]
        assert recovery["expired_tombstoned"] == 1
        assert recovery["live_preserved"] == 0
        assert recovery["consumed_preserved"] == 0
        assert recovery["tombstones_retained"] == 1
        assert recovery["tombstones_evicted"] == 0


def test_service_startup_preserves_valid_live_waiting_readiness(tokens):
    _relay, admin = tokens
    root = Path(os.environ["SARA_DATA_DIR"])
    store = DurableStore(root)
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    store.patch_registry(
        {
            FASA_EXECUTION_READINESS_REGISTRY_KEY: {
                "T-STARTUP-LIVE": {
                    "schema": FASA_EXECUTION_READINESS_RECORD_SCHEMA,
                    "status": "WAITING_ECHO",
                    "transition_id": "T-STARTUP-LIVE",
                    "action_id": "ACTION-STARTUP-LIVE",
                    "authorization_id": "AUTH-STARTUP-LIVE",
                    "provenance_event_id": "EVENT-STARTUP-LIVE",
                    "decision_digest_sha256": DIGEST,
                    "created_at": "2026-09-11T00:00:00Z",
                    "expires_at": future.isoformat().replace("+00:00", "Z"),
                }
            }
        }
    )

    with TestClient(app) as client:
        registry_response = client.get("/admin/registry", headers=_auth(admin))
        assert registry_response.status_code == 200
        registry = registry_response.json()["registry"]
        assert registry[FASA_EXECUTION_READINESS_REGISTRY_KEY]["T-STARTUP-LIVE"][
            "status"
        ] == "WAITING_ECHO"
        assert FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY not in registry

        audit_response = client.get("/v1/audit?limit=50", headers=_auth(admin))
        started = [
            record
            for record in audit_response.json()["records"]
            if record["event"] == "service_started"
        ]
        recovery = started[-1]["payload"]["fasa_readiness_recovery"]
        assert recovery["live_preserved"] == 1
        assert recovery["expired_tombstoned"] == 0
