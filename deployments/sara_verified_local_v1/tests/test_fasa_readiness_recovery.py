from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.fasa_readiness_recovery import (
    FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY,
    MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS,
    FASAReadinessRecoveryError,
    recover_execution_readiness_after_restart,
)
from worldshepherd_sara.fasa_runtime_gate import (
    FASA_EXECUTION_READINESS_RECORD_SCHEMA,
    FASA_EXECUTION_READINESS_REGISTRY_KEY,
    FASAEchoExecutionReadiness,
    FASARuntimeGateError,
    consume_execution_readiness,
)
from worldshepherd_sara.storage import DurableStore


DIGEST = "a" * 64
ECHO_DIGEST = "b" * 64


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _record(
    transition_id: str,
    *,
    status: str,
    created_at: datetime,
    expires_at: datetime,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": FASA_EXECUTION_READINESS_RECORD_SCHEMA,
        "status": status,
        "transition_id": transition_id,
        "action_id": f"ACTION-{transition_id}",
        "authorization_id": f"AUTH-{transition_id}",
        "provenance_event_id": f"EVENT-{transition_id}",
        "decision_digest_sha256": DIGEST,
        "created_at": _iso(created_at),
        "expires_at": _iso(expires_at),
    }
    if status in {"READY", "CONSUMED"}:
        record["echo_semantic_sha256"] = ECHO_DIGEST
        record["echo_acknowledged_at"] = _iso(created_at + timedelta(seconds=1))
    if status == "CONSUMED":
        record["execution_id"] = f"EXEC-{transition_id}"
        record["consumed_at"] = _iso(created_at + timedelta(seconds=2))
    return record


def _seed(store: DurableStore, records: dict[str, dict[str, object]]) -> None:
    store.patch_registry({FASA_EXECUTION_READINESS_REGISTRY_KEY: records})


def test_pristine_recovery_is_read_only(tmp_path):
    now = datetime(2026, 9, 11, 21, 15, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "sara")

    result = recover_execution_readiness_after_restart(store, now=now)

    assert result.live_preserved == 0
    assert result.consumed_preserved == 0
    assert result.expired_tombstoned == 0
    assert result.tombstones_retained == 0
    assert store.get_registry() == {}


def test_live_waiting_survives_restart_recovery(tmp_path):
    now = datetime(2026, 9, 11, 21, 20, tzinfo=timezone.utc)
    root = tmp_path / "sara"
    first = DurableStore(root)
    _seed(
        first,
        {
            "T-LIVE": _record(
                "T-LIVE",
                status="WAITING_ECHO",
                created_at=now - timedelta(seconds=5),
                expires_at=now + timedelta(seconds=30),
            )
        },
    )

    restarted = DurableStore(root)
    result = recover_execution_readiness_after_restart(restarted, now=now)

    assert result.live_preserved == 1
    assert result.expired_tombstoned == 0
    registry = restarted.get_registry()
    assert registry[FASA_EXECUTION_READINESS_REGISTRY_KEY]["T-LIVE"]["status"] == "WAITING_ECHO"
    assert FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY not in registry


def test_expired_waiting_moves_to_tombstone_and_recovery_is_idempotent(tmp_path):
    now = datetime(2026, 9, 11, 21, 25, tzinfo=timezone.utc)
    root = tmp_path / "sara"
    store = DurableStore(root)
    _seed(
        store,
        {
            "T-EXPIRED": _record(
                "T-EXPIRED",
                status="WAITING_ECHO",
                created_at=now - timedelta(minutes=2),
                expires_at=now - timedelta(seconds=1),
            )
        },
    )

    restarted = DurableStore(root)
    first = recover_execution_readiness_after_restart(restarted, now=now)
    second = recover_execution_readiness_after_restart(
        DurableStore(root),
        now=now + timedelta(seconds=1),
    )

    assert first.expired_tombstoned == 1
    assert second.expired_tombstoned == 0
    assert second.tombstones_retained == 1
    registry = DurableStore(root).get_registry()
    assert "T-EXPIRED" not in registry[FASA_EXECUTION_READINESS_REGISTRY_KEY]
    tombstone = registry[FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY]["T-EXPIRED"]
    assert tombstone["expired_from"] == "WAITING_ECHO"
    assert tombstone["authorization_id"] == "AUTH-T-EXPIRED"


def test_expired_ready_cannot_be_consumed_after_restart(tmp_path):
    now = datetime(2026, 9, 11, 21, 30, tzinfo=timezone.utc)
    root = tmp_path / "sara"
    store = DurableStore(root)
    _seed(
        store,
        {
            "T-READY": _record(
                "T-READY",
                status="READY",
                created_at=now - timedelta(minutes=1),
                expires_at=now - timedelta(seconds=1),
            )
        },
    )

    restarted = DurableStore(root)
    result = recover_execution_readiness_after_restart(restarted, now=now)
    assert result.expired_tombstoned == 1

    readiness = FASAEchoExecutionReadiness(
        transition_id="T-READY",
        action_id="ACTION-T-READY",
        authorization_id="AUTH-T-READY",
        provenance_event_id="EVENT-T-READY",
        decision_digest_sha256=DIGEST,
        echo_semantic_sha256=ECHO_DIGEST,
        echo_delivery_count=1,
        acknowledged_at=now - timedelta(seconds=30),
        expires_at=now - timedelta(seconds=1),
    )
    with pytest.raises(FASARuntimeGateError, match="unavailable"):
        consume_execution_readiness(
            restarted,
            readiness=readiness,
            execution_id="EXEC-REPLAY",
            now=now + timedelta(seconds=1),
        )


def test_consumed_authority_is_preserved_and_never_resurrected(tmp_path):
    now = datetime(2026, 9, 11, 21, 35, tzinfo=timezone.utc)
    root = tmp_path / "sara"
    store = DurableStore(root)
    _seed(
        store,
        {
            "T-CONSUMED": _record(
                "T-CONSUMED",
                status="CONSUMED",
                created_at=now - timedelta(minutes=2),
                expires_at=now - timedelta(minutes=1),
            )
        },
    )

    result = recover_execution_readiness_after_restart(DurableStore(root), now=now)

    assert result.consumed_preserved == 1
    assert result.expired_tombstoned == 0
    registry = DurableStore(root).get_registry()
    assert registry[FASA_EXECUTION_READINESS_REGISTRY_KEY]["T-CONSUMED"]["status"] == "CONSUMED"
    assert FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY not in registry


def test_expiry_tombstones_are_bounded_without_evicting_live_state(tmp_path):
    now = datetime(2026, 9, 11, 21, 40, tzinfo=timezone.utc)
    root = tmp_path / "sara"
    store = DurableStore(root)
    records: dict[str, dict[str, object]] = {
        "T-LIVE": _record(
            "T-LIVE",
            status="WAITING_ECHO",
            created_at=now - timedelta(seconds=1),
            expires_at=now + timedelta(minutes=1),
        )
    }
    for index in range(MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS + 3):
        transition_id = f"T-OLD-{index:02d}"
        records[transition_id] = _record(
            transition_id,
            status="WAITING_ECHO",
            created_at=now - timedelta(minutes=5, seconds=index),
            expires_at=now - timedelta(minutes=1, seconds=index),
        )
    _seed(store, records)

    result = recover_execution_readiness_after_restart(DurableStore(root), now=now)

    assert result.live_preserved == 1
    assert result.expired_tombstoned == MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS + 3
    assert result.tombstones_retained == MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS
    assert result.tombstones_evicted == 3
    registry = DurableStore(root).get_registry()
    assert registry[FASA_EXECUTION_READINESS_REGISTRY_KEY]["T-LIVE"]["status"] == "WAITING_ECHO"
    assert len(registry[FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY]) == MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS


def test_malformed_readiness_fails_closed_without_partial_cleanup(tmp_path):
    now = datetime(2026, 9, 11, 21, 45, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "sara")
    store.patch_registry(
        {
            FASA_EXECUTION_READINESS_REGISTRY_KEY: {
                "T-BAD": {
                    "schema": FASA_EXECUTION_READINESS_RECORD_SCHEMA,
                    "status": "READY",
                    "transition_id": "T-BAD",
                }
            }
        }
    )

    with pytest.raises(FASAReadinessRecoveryError, match="recovery aborted"):
        recover_execution_readiness_after_restart(store, now=now)

    registry = store.get_registry()
    assert "T-BAD" in registry[FASA_EXECUTION_READINESS_REGISTRY_KEY]
    assert FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY not in registry
