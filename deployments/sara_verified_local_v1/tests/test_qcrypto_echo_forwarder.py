from __future__ import annotations

import pytest

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.qcrypto_echo_config import (
    ECHO_FORWARD_TOKEN_FILE_ENV,
    ECHO_PERSISTENCE_URL_ENV,
    _validated_url,
    forwarder_from_environment,
)
from worldshepherd_sara.qcrypto_echo_forwarder import (
    QCryptoEchoConflict,
    QCryptoEchoForwarder,
    QCryptoEchoForwarderError,
)


EVENTS = (
    "qcrypto_echo_state",
    "qcrypto_prime_state",
    "qcrypto_sara_state",
    "qcrypto_overwatch_state",
)


def records() -> list[AuditRecord]:
    return [
        AuditRecord(
            timestamp=f"2026-09-14T10:00:0{index}+00:00",
            event=event,
            actor="admin_operator",
            payload={
                "_outbox_event_id": f"SARA-EVENT-QCRYPTO-SYNC-{index}",
                "_delivery_semantics": "AT_LEAST_ONCE",
                "decision_digest": "sha256:" + "1" * 64,
                "execution_authority": False,
                "live_value_authorized": False,
            },
        )
        for index, event in enumerate(EVENTS)
    ]


def reconciliation(payload, *, echo_only: int = 0):
    submitted = [item["payload"]["_outbox_event_id"] for item in payload["records"]]
    entries = [
        {"event_id": event_id, "classification": "MATCHED"}
        for event_id in submitted
    ]
    entries.extend(
        {
            "event_id": f"SARA-EVENT-RETAINED-{index}",
            "classification": "ECHO_ONLY",
        }
        for index in range(echo_only)
    )
    return {
        "schema": "WS-ECHO-SARA-RECONCILIATION-V1",
        "scope": "PROVIDED_SARA_AUDIT_WINDOW",
        "counts": {
            "MATCHED": 4,
            "SARA_ONLY": 0,
            "ECHO_ONLY": echo_only,
            "PAYLOAD_MISMATCH": 0,
        },
        "entries": entries,
    }


def success_transport(base_url, path, payload, token):
    assert base_url == "http://echo:9550"
    assert token == "e" * 40
    if path == "/v1/ingest":
        return 200, {
            "outcome": "STORED",
            "event_id": payload["payload"]["_outbox_event_id"],
        }
    assert path == "/v1/reconcile"
    return 200, reconciliation(payload)


def test_forwarder_requires_all_submitted_records_to_match():
    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=success_transport,
    )
    result = forwarder.sync(records())
    assert result.stored == 4
    assert result.deduplicated == 0
    assert len(result.event_ids) == 4
    assert result.to_dict()["execution_authority"] is False
    assert result.to_dict()["live_value_authorized"] is False


def test_forwarder_accepts_unrelated_retained_echo_history():
    def transport(base_url, path, payload, token):
        if path == "/v1/ingest":
            return 200, {
                "outcome": "STORED",
                "event_id": payload["payload"]["_outbox_event_id"],
            }
        return 200, reconciliation(payload, echo_only=17)

    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=transport,
    )
    result = forwarder.sync(records())
    assert result.reconciliation["counts"] == {
        "MATCHED": 4,
        "SARA_ONLY": 0,
        "ECHO_ONLY": 17,
        "PAYLOAD_MISMATCH": 0,
    }


def test_forwarder_recovers_after_partial_delivery_without_duplicate_semantics():
    stored_ids: set[str] = set()
    ingest_calls = 0
    fail_once = True

    def transport(base_url, path, payload, token):
        nonlocal ingest_calls, fail_once
        assert base_url == "http://echo:9550"
        assert token == "e" * 40
        if path == "/v1/ingest":
            ingest_calls += 1
            event_id = payload["payload"]["_outbox_event_id"]
            # First attempt stores records 1 and 2, then the transport fails
            # before record 3 is accepted. The caller receives no success.
            if fail_once and ingest_calls == 3:
                fail_once = False
                return 503, {"detail": "simulated mid-batch interruption"}
            if event_id in stored_ids:
                outcome = "DEDUPLICATED"
            else:
                stored_ids.add(event_id)
                outcome = "STORED"
            return 200, {"outcome": outcome, "event_id": event_id}
        assert path == "/v1/reconcile"
        assert stored_ids == {
            "SARA-EVENT-QCRYPTO-SYNC-0",
            "SARA-EVENT-QCRYPTO-SYNC-1",
            "SARA-EVENT-QCRYPTO-SYNC-2",
            "SARA-EVENT-QCRYPTO-SYNC-3",
        }
        return 200, reconciliation(payload, echo_only=2)

    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=transport,
    )
    source = records()

    with pytest.raises(QCryptoEchoForwarderError, match="HTTP 503"):
        forwarder.sync(source)
    assert stored_ids == {
        "SARA-EVENT-QCRYPTO-SYNC-0",
        "SARA-EVENT-QCRYPTO-SYNC-1",
    }

    recovered = forwarder.sync(source)
    assert recovered.stored == 2
    assert recovered.deduplicated == 2
    assert set(recovered.event_ids) == stored_ids
    assert recovered.reconciliation["counts"] == {
        "MATCHED": 4,
        "SARA_ONLY": 0,
        "ECHO_ONLY": 2,
        "PAYLOAD_MISMATCH": 0,
    }


def test_forwarder_rejects_reconciliation_gap():
    def transport(base_url, path, payload, token):
        if path == "/v1/ingest":
            return 200, {
                "outcome": "STORED",
                "event_id": payload["payload"]["_outbox_event_id"],
            }
        body = reconciliation(payload)
        body["counts"]["MATCHED"] = 3
        body["counts"]["SARA_ONLY"] = 1
        body["entries"][0]["classification"] = "SARA_ONLY"
        return 200, body

    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=transport,
    )
    with pytest.raises(QCryptoEchoForwarderError, match="all four submitted records"):
        forwarder.sync(records())


def test_forwarder_rejects_missing_submitted_event_entry_even_when_counts_claim_match():
    def transport(base_url, path, payload, token):
        if path == "/v1/ingest":
            return 200, {
                "outcome": "STORED",
                "event_id": payload["payload"]["_outbox_event_id"],
            }
        body = reconciliation(payload, echo_only=1)
        body["entries"] = body["entries"][1:]
        return 200, body

    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=transport,
    )
    with pytest.raises(QCryptoEchoForwarderError, match="omitted"):
        forwarder.sync(records())


def test_forwarder_rejects_wrong_reconciliation_schema_or_scope():
    def bad_schema(base_url, path, payload, token):
        if path == "/v1/ingest":
            return 200, {
                "outcome": "STORED",
                "event_id": payload["payload"]["_outbox_event_id"],
            }
        body = reconciliation(payload)
        body["schema"] = "UNSUPPORTED"
        return 200, body

    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=bad_schema,
    )
    with pytest.raises(QCryptoEchoForwarderError, match="unsupported schema"):
        forwarder.sync(records())


def test_forwarder_maps_echo_conflict_to_fail_closed_error():
    def transport(base_url, path, payload, token):
        return 409, {"detail": "conflict"}

    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=transport,
    )
    with pytest.raises(QCryptoEchoConflict):
        forwarder.sync(records())


def test_url_policy_allows_local_http_and_requires_tls_off_box():
    assert _validated_url("http://echo:9550") == "http://echo:9550"
    assert _validated_url("http://127.0.0.1:9550/") == "http://127.0.0.1:9550"
    assert _validated_url("https://echo.example.test") == "https://echo.example.test"
    with pytest.raises(QCryptoEchoForwarderError, match="cleartext"):
        _validated_url("http://echo.example.test:9550")
    with pytest.raises(QCryptoEchoForwarderError, match="forbidden"):
        _validated_url("https://user:password@echo.example.test")
    with pytest.raises(QCryptoEchoForwarderError, match="application path"):
        _validated_url("https://echo.example.test/v1")


def test_environment_configuration_uses_locked_independent_token_file(tmp_path, monkeypatch):
    token_path = tmp_path / "echo-forward-token"
    token_path.write_text("e" * 40 + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    monkeypatch.setenv(ECHO_PERSISTENCE_URL_ENV, "http://echo:9550")
    monkeypatch.setenv(ECHO_FORWARD_TOKEN_FILE_ENV, str(token_path.resolve()))
    monkeypatch.setenv("SARA_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("SARA_RELAY_TOKEN", "r" * 40)

    forwarder = forwarder_from_environment()
    assert forwarder is not None
    assert forwarder.base_url == "http://echo:9550"

    monkeypatch.setenv("SARA_ADMIN_TOKEN", "e" * 40)
    with pytest.raises(QCryptoEchoForwarderError, match="independent"):
        forwarder_from_environment()


def test_environment_configuration_is_optional_but_not_partial(monkeypatch):
    monkeypatch.delenv(ECHO_PERSISTENCE_URL_ENV, raising=False)
    monkeypatch.delenv(ECHO_FORWARD_TOKEN_FILE_ENV, raising=False)
    assert forwarder_from_environment() is None

    monkeypatch.setenv(ECHO_PERSISTENCE_URL_ENV, "http://echo:9550")
    with pytest.raises(QCryptoEchoForwarderError, match="incomplete"):
        forwarder_from_environment()
