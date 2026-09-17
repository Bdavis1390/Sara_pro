from __future__ import annotations

import base64
import importlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.storage import DurableStore
from worldshepherd_sara.trust_root_guard import (
    PRIME_TRUST_ROOT_STATE_KEY,
    PrimeTrustRootError,
    guard_prime_trust_root,
    reconcile_prime_trust_root,
    trust_root_state_from_environment,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _pub() -> str:
    return _b64url(Ed25519PrivateKey.generate().public_key().public_bytes_raw())


def env(*, epoch: int | None, keys: dict[str, str] | None = None, revoked=()) -> dict[str, str]:
    values = {
        "PRIME_SENTINEL_PUBLIC_KEYS_JSON": json.dumps(keys or {}),
        "PRIME_SENTINEL_REVOKED_KEY_IDS": ",".join(revoked),
    }
    if epoch is not None:
        values["PRIME_SENTINEL_TRUST_EPOCH"] = str(epoch)
    return values


def test_initializes_matches_and_survives_restart(tmp_path):
    key = _pub()
    store = DurableStore(tmp_path / "sara")

    first = guard_prime_trust_root(
        store,
        environ=env(epoch=1, keys={"PS-K1": key}),
    )
    assert first["status"] == "INITIALIZED"
    assert first["epoch"] == 1

    restarted = DurableStore(store.root)
    second = guard_prime_trust_root(
        restarted,
        environ=env(epoch=1, keys={"PS-K1": key}),
    )
    assert second["status"] == "MATCHED"
    state = restarted.get_registry()[PRIME_TRUST_ROOT_STATE_KEY]
    assert state["epoch"] == 1
    assert set(state["key_fingerprints_sha256"]) == {"PS-K1"}


def test_configured_trust_root_requires_positive_epoch():
    key = _pub()
    with pytest.raises(PrimeTrustRootError, match="required"):
        trust_root_state_from_environment(env(epoch=None, keys={"PS-K1": key}))

    with pytest.raises(PrimeTrustRootError, match="positive integer"):
        trust_root_state_from_environment(env(epoch=0, keys={"PS-K1": key}))


def test_lower_epoch_rollback_fails_closed(tmp_path):
    key = _pub()
    store = DurableStore(tmp_path / "sara")
    guard_prime_trust_root(store, environ=env(epoch=3, keys={"PS-K1": key}))

    with pytest.raises(PrimeTrustRootError, match="epoch rollback"):
        guard_prime_trust_root(store, environ=env(epoch=2, keys={"PS-K1": key}))


def test_same_epoch_material_mutation_fails_closed(tmp_path):
    store = DurableStore(tmp_path / "sara")
    guard_prime_trust_root(
        store,
        environ=env(epoch=4, keys={"PS-K1": _pub()}),
    )

    with pytest.raises(PrimeTrustRootError, match="without epoch advance"):
        guard_prime_trust_root(
            store,
            environ=env(epoch=4, keys={"PS-K2": _pub()}),
        )


def test_key_id_rebinding_is_rejected_even_with_higher_epoch(tmp_path):
    store = DurableStore(tmp_path / "sara")
    guard_prime_trust_root(
        store,
        environ=env(epoch=1, keys={"PS-K1": _pub()}),
    )

    with pytest.raises(PrimeTrustRootError, match="cannot be rebound"):
        guard_prime_trust_root(
            store,
            environ=env(epoch=2, keys={"PS-K1": _pub()}),
        )


def test_revocation_rollback_is_rejected(tmp_path):
    key = _pub()
    store = DurableStore(tmp_path / "sara")
    guard_prime_trust_root(
        store,
        environ=env(epoch=2, keys={"PS-K1": key}, revoked=("PS-OLD",)),
    )

    with pytest.raises(PrimeTrustRootError, match="revocation rollback"):
        guard_prime_trust_root(
            store,
            environ=env(epoch=3, keys={"PS-K1": key}, revoked=()),
        )


def test_removed_key_must_remain_explicitly_revoked(tmp_path):
    first = _pub()
    second = _pub()
    store = DurableStore(tmp_path / "sara")
    guard_prime_trust_root(
        store,
        environ=env(epoch=1, keys={"PS-K1": first, "PS-K2": second}),
    )

    with pytest.raises(PrimeTrustRootError, match="must remain explicitly revoked"):
        guard_prime_trust_root(
            store,
            environ=env(epoch=2, keys={"PS-K2": second}),
        )


def test_forward_rotation_adds_key_and_revokes_removed_key(tmp_path):
    first = _pub()
    second = _pub()
    store = DurableStore(tmp_path / "sara")
    guard_prime_trust_root(
        store,
        environ=env(epoch=1, keys={"PS-K1": first}),
    )

    result = guard_prime_trust_root(
        store,
        environ=env(
            epoch=2,
            keys={"PS-K2": second},
            revoked=("PS-K1",),
        ),
    )

    assert result["status"] == "ADVANCED"
    assert result["previous_epoch"] == 1
    assert result["epoch"] == 2
    state = store.get_registry()[PRIME_TRUST_ROOT_STATE_KEY]
    assert state["revoked_key_ids"] == ["PS-K1"]
    assert set(state["key_fingerprints_sha256"]) == {"PS-K2"}


def test_removing_all_runtime_trust_config_after_initialization_fails(tmp_path):
    store = DurableStore(tmp_path / "sara")
    guard_prime_trust_root(
        store,
        environ=env(epoch=1, keys={"PS-K1": _pub()}),
    )

    with pytest.raises(PrimeTrustRootError, match="missing after prior initialization"):
        guard_prime_trust_root(store, environ={})


def test_unconfigured_runtime_without_prior_state_is_allowed_and_audited(tmp_path):
    store = DurableStore(tmp_path / "sara")
    result = guard_prime_trust_root(store, environ={})

    assert result == {
        "status": "UNCONFIGURED",
        "epoch": None,
        "material_sha256": None,
    }
    audit = store.read_audit(10)
    assert audit[-1]["event"] == "prime_trust_root_guard_evaluated"
    assert audit[-1]["payload"]["status"] == "UNCONFIGURED"


def test_stored_trust_root_state_is_digest_self_checking():
    key = _pub()
    current = trust_root_state_from_environment(env(epoch=1, keys={"PS-K1": key}))
    assert current is not None
    tampered = dict(current)
    tampered["material_sha256"] = "0" * 64

    with pytest.raises(PrimeTrustRootError, match="digest does not match"):
        reconcile_prime_trust_root(
            {PRIME_TRUST_ROOT_STATE_KEY: tampered},
            current,
        )


def test_declared_rollback_classes_drop_by_more_than_ten_x(tmp_path):
    baseline_classes = 4
    residual = 0

    # 1. lower epoch rollback
    key = _pub()
    store = DurableStore(tmp_path / "epoch")
    guard_prime_trust_root(store, environ=env(epoch=2, keys={"PS-K1": key}))
    try:
        guard_prime_trust_root(store, environ=env(epoch=1, keys={"PS-K1": key}))
        residual += 1
    except PrimeTrustRootError:
        pass

    # 2. same-epoch material mutation
    store = DurableStore(tmp_path / "mutation")
    guard_prime_trust_root(store, environ=env(epoch=1, keys={"PS-K1": _pub()}))
    try:
        guard_prime_trust_root(store, environ=env(epoch=1, keys={"PS-K2": _pub()}))
        residual += 1
    except PrimeTrustRootError:
        pass

    # 3. higher-epoch key-ID rebinding
    store = DurableStore(tmp_path / "rebind")
    guard_prime_trust_root(store, environ=env(epoch=1, keys={"PS-K1": _pub()}))
    try:
        guard_prime_trust_root(store, environ=env(epoch=2, keys={"PS-K1": _pub()}))
        residual += 1
    except PrimeTrustRootError:
        pass

    # 4. revocation rollback
    key = _pub()
    store = DurableStore(tmp_path / "revocation")
    guard_prime_trust_root(
        store,
        environ=env(epoch=1, keys={"PS-K1": key}, revoked=("PS-OLD",)),
    )
    try:
        guard_prime_trust_root(
            store,
            environ=env(epoch=2, keys={"PS-K1": key}, revoked=()),
        )
        residual += 1
    except PrimeTrustRootError:
        pass

    assert baseline_classes == 4
    assert residual / baseline_classes <= 0.10
    assert residual == 0



def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_trust_root_namespace_is_protected_from_generic_admin_patch(client, tokens):
    _relay, admin = tokens
    response = client.patch(
        "/admin/registry",
        headers=_auth(admin),
        json={
            "values": {
                PRIME_TRUST_ROOT_STATE_KEY: {
                    "schema": "attacker-controlled",
                    "epoch": 999,
                }
            }
        },
    )

    assert response.status_code == 403
    assert PRIME_TRUST_ROOT_STATE_KEY in response.json()["detail"]


def test_health_reports_bounded_trust_root_guard_state(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()

    guard = body["prime_trust_root_guard"]
    assert guard["status"] == "UNCONFIGURED"
    assert guard["epoch"] is None
    assert guard["material_sha256"] is None



def test_trust_root_admission_precedes_outbox_replay(monkeypatch, tmp_path):
    app_module = importlib.import_module("worldshepherd_sara.app")
    order: list[str] = []

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

    def fake_guard(store):
        order.append("guard")
        return {
            "status": "UNCONFIGURED",
            "epoch": None,
            "material_sha256": None,
        }

    def fake_drain(store, *, limit):
        order.append("drain")
        return 0

    monkeypatch.setattr(app_module, "guard_prime_trust_root", fake_guard)
    monkeypatch.setattr(app_module, "drain_event_outbox", fake_drain)

    with TestClient(app_module.app):
        assert order[:2] == ["guard", "drain"]
