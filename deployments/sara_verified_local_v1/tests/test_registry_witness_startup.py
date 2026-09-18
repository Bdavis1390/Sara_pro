from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from worldshepherd_sara.registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryWitnessRollbackDetected,
)
from worldshepherd_sara.registry_witness_startup import (
    RegistryWitnessStartupError,
    enforce_registry_witness_startup,
)
from worldshepherd_sara.storage import DurableStore


class _Client:
    def __init__(self, *, assessment=None, error=None):
        self.assessment = assessment
        self.error = error
        self.check_calls = 0
        self.advance_calls = 0

    def check(self, local_status, *, require_head=True):
        self.check_calls += 1
        assert require_head is True
        assert local_status["generation"] >= 0
        if self.error is not None:
            raise self.error
        return dict(self.assessment)

    def advance_and_verify(self, local_status):
        self.advance_calls += 1
        raise AssertionError("startup must never auto-advance the witness")


def _pass_assessment(generation: int = 0):
    return {
        "status": "PASS",
        "generation": generation,
        "state_root_sha256": "a" * 64,
        "commit_hash": "b" * 64,
        "witness_id": "WS-G9E-TEST",
        "witness_mode": REMOTE_WITNESS_MODE,
        "witness_receipt_sha256": "c" * 64,
        "signature_verified": True,
        "monotonic_match": True,
        "external_witnessed": False,
        "independence_verified": False,
    }


def test_disabled_witness_mode_does_not_load_client(tmp_path):
    store = DurableStore(tmp_path / "sara")

    def forbidden_loader():
        raise AssertionError("disabled witness mode must not load a client")

    result = enforce_registry_witness_startup(
        store,
        environ={},
        client_loader=forbidden_loader,
    )

    assert result["status"] == "DISABLED"
    assert result["required"] is False


def test_required_exact_remote_witness_passes_and_emits_bounded_evidence(tmp_path):
    store = DurableStore(tmp_path / "sara")
    generation = store.checkpoint_status()["generation"]
    client = _Client(assessment=_pass_assessment(generation))

    result = enforce_registry_witness_startup(
        store,
        environ={"SARA_REQUIRE_REGISTRY_WITNESS": "1"},
        client_loader=lambda: client,
    )

    assert result == {
        "status": "PASS",
        "required": True,
        "generation": generation,
        "witness_id": "WS-G9E-TEST",
        "witness_mode": REMOTE_WITNESS_MODE,
        "witness_receipt_sha256": "c" * 64,
        "signature_verified": True,
        "monotonic_match": True,
    }
    assert client.check_calls == 1
    assert client.advance_calls == 0

    audit = store.read_audit(10)[-1]
    assert audit["event"] == "registry_witness_startup_verified"
    assert audit["payload"] == result


def test_locally_newer_checkpoint_requires_explicit_operator_advance(tmp_path):
    store = DurableStore(tmp_path / "sara")
    client = _Client(
        assessment={
            "status": "NEEDS_WITNESS_ADVANCE",
            "generation": store.checkpoint_status()["generation"],
            "witness_generation": 0,
            "witness_id": "WS-G9E-TEST",
            "witness_mode": REMOTE_WITNESS_MODE,
            "witness_receipt_sha256": "d" * 64,
            "signature_verified": True,
            "monotonic_match": False,
            "external_witnessed": False,
            "independence_verified": False,
        }
    )

    with pytest.raises(
        RegistryWitnessStartupError,
        match="not yet covered",
    ) as caught:
        enforce_registry_witness_startup(
            store,
            environ={"SARA_REQUIRE_REGISTRY_WITNESS": "true"},
            client_loader=lambda: client,
        )

    assert caught.value.reason_code == "WITNESS_ADVANCE_REQUIRED"
    assert client.check_calls == 1
    assert client.advance_calls == 0


def test_newer_remote_witness_maps_to_local_rollback_rejection(tmp_path):
    store = DurableStore(tmp_path / "sara")
    client = _Client(
        error=RegistryWitnessRollbackDetected(
            "local registry generation is older than signed monotonic witness head"
        )
    )

    with pytest.raises(RegistryWitnessStartupError) as caught:
        enforce_registry_witness_startup(
            store,
            environ={"SARA_REQUIRE_REGISTRY_WITNESS": "on"},
            client_loader=lambda: client,
        )

    assert caught.value.reason_code == "LOCAL_REGISTRY_ROLLBACK_DETECTED"
    record = store.read_audit(10)[-1]
    assert record["event"] == "registry_witness_startup_rejected"
    assert record["payload"] == {
        "status": "REJECTED",
        "reason_code": "LOCAL_REGISTRY_ROLLBACK_DETECTED",
    }
    assert "generation is older" not in str(record)


def test_test_only_witness_mode_cannot_satisfy_required_startup(tmp_path):
    store = DurableStore(tmp_path / "sara")
    assessment = _pass_assessment(store.checkpoint_status()["generation"])
    assessment["witness_mode"] = "TEST_ONLY_IN_PROCESS"
    client = _Client(assessment=assessment)

    with pytest.raises(RegistryWitnessStartupError) as caught:
        enforce_registry_witness_startup(
            store,
            environ={"SARA_REQUIRE_REGISTRY_WITNESS": "yes"},
            client_loader=lambda: client,
        )

    assert caught.value.reason_code == "WITNESS_MODE_INVALID"


def test_invalid_requirement_value_fails_closed_with_bounded_reason(tmp_path):
    store = DurableStore(tmp_path / "sara")

    with pytest.raises(RegistryWitnessStartupError) as caught:
        enforce_registry_witness_startup(
            store,
            environ={"SARA_REQUIRE_REGISTRY_WITNESS": "sometimes"},
        )

    assert caught.value.reason_code == "WITNESS_REQUIREMENT_INVALID"
    assert store.read_audit(10)[-1]["payload"] == {
        "status": "REJECTED",
        "reason_code": "WITNESS_REQUIREMENT_INVALID",
    }


def _configure_app_env(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "SARA_RELAY_TOKEN",
        "relay-token-0123456789abcdef012345",
    )
    monkeypatch.setenv(
        "SARA_ADMIN_TOKEN",
        "admin-token-0123456789abcdef012345",
    )
    monkeypatch.setenv("SARA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", raising=False)
    monkeypatch.delenv("PRIME_SENTINEL_REVOKED_KEY_IDS", raising=False)
    monkeypatch.delenv("PRIME_SENTINEL_TRUST_EPOCH", raising=False)
    monkeypatch.delenv("SARA_REQUIRE_REGISTRY_WITNESS", raising=False)


def test_app_startup_order_is_guard_witness_verifier_then_replay(monkeypatch, tmp_path):
    app_module = importlib.import_module("worldshepherd_sara.app")
    _configure_app_env(monkeypatch, tmp_path)
    order: list[str] = []

    def fake_guard(store):
        order.append("guard")
        return {
            "status": "UNCONFIGURED",
            "epoch": None,
            "material_sha256": None,
        }

    def fake_witness(store):
        order.append("witness")
        return {
            "status": "DISABLED",
            "required": False,
            "generation": None,
            "witness_id": None,
            "witness_mode": None,
            "witness_receipt_sha256": None,
            "signature_verified": False,
            "monotonic_match": False,
        }

    class FakeVerifier:
        configured = False

    def fake_verifier():
        order.append("verifier")
        return FakeVerifier()

    def fake_drain(store, *, limit):
        order.append("drain")
        return 0

    monkeypatch.setattr(app_module, "guard_prime_trust_root", fake_guard)
    monkeypatch.setattr(app_module, "enforce_registry_witness_startup", fake_witness)
    monkeypatch.setattr(
        app_module.PrimeSentinelVerifier,
        "from_environment",
        fake_verifier,
    )
    monkeypatch.setattr(app_module, "drain_event_outbox", fake_drain)

    with TestClient(app_module.app):
        assert order[:4] == ["guard", "witness", "verifier", "drain"]


def test_witness_rejection_prevents_verifier_and_outbox_replay(monkeypatch, tmp_path):
    app_module = importlib.import_module("worldshepherd_sara.app")
    _configure_app_env(monkeypatch, tmp_path)
    calls: list[str] = []

    def fake_guard(store):
        calls.append("guard")
        return {
            "status": "MATCHED",
            "epoch": 1,
            "material_sha256": "a" * 64,
        }

    def reject_witness(store):
        calls.append("witness")
        raise RegistryWitnessStartupError(
            "LOCAL_REGISTRY_ROLLBACK_DETECTED",
            "rollback",
        )

    def forbidden_verifier():
        calls.append("verifier")
        raise AssertionError("verifier must not be constructed after witness rejection")

    def forbidden_drain(store, *, limit):
        calls.append("drain")
        raise AssertionError("outbox must not replay after witness rejection")

    monkeypatch.setattr(app_module, "guard_prime_trust_root", fake_guard)
    monkeypatch.setattr(app_module, "enforce_registry_witness_startup", reject_witness)
    monkeypatch.setattr(
        app_module.PrimeSentinelVerifier,
        "from_environment",
        forbidden_verifier,
    )
    monkeypatch.setattr(app_module, "drain_event_outbox", forbidden_drain)

    with pytest.raises(RegistryWitnessStartupError):
        with TestClient(app_module.app):
            pass

    assert calls == ["guard", "witness"]
