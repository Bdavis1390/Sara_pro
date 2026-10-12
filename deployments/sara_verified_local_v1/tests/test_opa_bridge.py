from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from worldshepherd_sara.opa_bridge import evaluate_boolean_policy, validate_endpoint


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_loopback_endpoint_allowed_by_default() -> None:
    endpoint = "http://127.0.0.1:8181/v1/data/worldshepherd/allow"
    assert validate_endpoint(endpoint) == endpoint


def test_remote_endpoint_blocked_without_explicit_override() -> None:
    with pytest.raises(ValueError, match="remote OPA endpoint blocked"):
        validate_endpoint("https://opa.example.com/v1/data/worldshepherd/allow")


def test_credentials_in_url_rejected() -> None:
    with pytest.raises(ValueError, match="credentials"):
        validate_endpoint("http://user:pass@127.0.0.1:8181/v1/data/x")


def test_boolean_allow_receipt_binds_decision_id_and_request_hash() -> None:
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return FakeResponse({"result": True, "decision_id": "decision-123"})

    receipt = evaluate_boolean_policy(
        endpoint="http://localhost:8181/v1/data/worldshepherd/allow",
        input_document={"actor": "operator", "action": "read"},
        opener=opener,
        now=lambda: datetime(2026, 9, 17, 21, 0, tzinfo=timezone.utc),
    )

    assert receipt["decision"] == "ALLOW"
    assert receipt["opa_result"] is True
    assert receipt["decision_id"] == "decision-123"
    assert len(receipt["request_sha256"]) == 64
    assert calls[0][1] == 5.0


def test_boolean_deny_is_preserved_not_raised() -> None:
    def opener(request, timeout):
        return FakeResponse({"result": False, "decision_id": "deny-1"})

    receipt = evaluate_boolean_policy(
        endpoint="http://localhost:8181/v1/data/worldshepherd/allow",
        input_document={"action": "prohibited"},
        opener=opener,
    )
    assert receipt["decision"] == "DENY"
    assert receipt["opa_result"] is False


def test_missing_result_fails_closed() -> None:
    def opener(request, timeout):
        return FakeResponse({"decision_id": "missing-result"})

    with pytest.raises(RuntimeError, match="missing required result"):
        evaluate_boolean_policy(
            endpoint="http://localhost:8181/v1/data/worldshepherd/allow",
            input_document={},
            opener=opener,
        )


def test_non_boolean_result_fails_closed() -> None:
    def opener(request, timeout):
        return FakeResponse({"result": {"allow": True}})

    with pytest.raises(RuntimeError, match="boolean result"):
        evaluate_boolean_policy(
            endpoint="http://localhost:8181/v1/data/worldshepherd/allow",
            input_document={},
            opener=opener,
        )


def test_transport_failure_fails_closed() -> None:
    def opener(request, timeout):
        raise OSError("connection refused")

    with pytest.raises(RuntimeError, match="connection refused"):
        evaluate_boolean_policy(
            endpoint="http://localhost:8181/v1/data/worldshepherd/allow",
            input_document={},
            opener=opener,
        )
