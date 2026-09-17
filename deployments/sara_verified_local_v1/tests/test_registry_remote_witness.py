from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryMonotonicWitnessVerifier,
    RegistryWitnessConflict,
    RegistryWitnessCoordinates,
    RegistryWitnessRollbackDetected,
    RegistryWitnessUnavailable,
)
from worldshepherd_sara.registry_witness_http import (
    HttpsRegistryWitnessTransport,
    RegistryWitnessTransportConfigError,
)
from worldshepherd_sara.registry_witness_service import (
    RegistryWitnessLedger,
    RegistryWitnessService,
    RegistryWitnessServiceConfigError,
    create_registry_witness_app,
)


WITNESS_ID = "WS-MAG-1-6R"
KEY_ID = "WS-MAG-1-6R-KEY"
NAMESPACE = "worldshepherd/sara/registry"
TOKEN = "registry-witness-test-token-0123456789abcdef"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _h(character: str) -> str:
    return character * 64


def _ledger(tmp_path, private_key):
    return RegistryWitnessLedger(
        tmp_path / "remote-witness" / "witness.db",
        private_key=private_key,
        witness_id=WITNESS_ID,
        key_id=KEY_ID,
        namespace=NAMESPACE,
    )


def _verifier(private_key):
    return RegistryMonotonicWitnessVerifier(
        public_keys_b64url={
            KEY_ID: _b64url(private_key.public_key().public_bytes_raw()),
        },
        expected_witness_id=WITNESS_ID,
        expected_namespace=NAMESPACE,
    )


def test_durable_witness_persists_monotonic_head_and_hash_chain_across_restart(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    first_ledger = _ledger(tmp_path, private_key)

    first = first_ledger.witness(
        RegistryWitnessCoordinates(7, _h("a"), _h("b"))
    )
    assert first["generation"] == 7
    assert first["witness_mode"] == REMOTE_WITNESS_MODE

    restarted = _ledger(tmp_path, private_key)
    assert restarted.read_head() == first

    repeated = restarted.witness(
        RegistryWitnessCoordinates(7, _h("a"), _h("b"))
    )
    assert repeated == first

    second = restarted.witness(
        RegistryWitnessCoordinates(8, _h("c"), _h("d"))
    )
    assert second["generation"] == 8
    assert second["previous_receipt_sha256"] == first["receipt_sha256"]
    assert restarted.read_head() == second

    verifier = _verifier(private_key)
    verified = verifier.verify_receipt(second)
    assert verified["receipt_sha256"] == second["receipt_sha256"]


def test_durable_witness_rejects_rollback_and_same_generation_conflict(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    ledger = _ledger(tmp_path, private_key)
    ledger.witness(RegistryWitnessCoordinates(4, _h("1"), _h("2")))

    with pytest.raises(RegistryWitnessRollbackDetected, match="lower than its durable head"):
        ledger.witness(RegistryWitnessCoordinates(3, _h("3"), _h("4")))

    with pytest.raises(RegistryWitnessConflict, match="same generation"):
        ledger.witness(RegistryWitnessCoordinates(4, _h("5"), _h("2")))


def test_witness_ledger_binds_key_identity_and_configuration(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    _ledger(tmp_path, private_key)

    replacement_key = Ed25519PrivateKey.generate()
    with pytest.raises(RegistryWitnessServiceConfigError, match="metadata mismatch"):
        _ledger(tmp_path, replacement_key)


def test_service_requires_bearer_and_exposes_signed_monotonic_receipts(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    service = RegistryWitnessService(
        ledger=_ledger(tmp_path, private_key),
        service_token=TOKEN,
    )
    client = TestClient(create_registry_witness_app(service))

    assert client.get("/health").json()["independence_verified"] is False
    public_key = client.get("/v1/public-key").json()
    assert public_key["key_id"] == KEY_ID
    assert "does not establish independent administration" in public_key["claims_boundary"]

    assert client.get("/v1/head").status_code == 401
    assert client.get(
        "/v1/head",
        headers={"Authorization": "Bearer wrong-token-that-is-long-enough-000000"},
    ).status_code == 403

    headers = {"Authorization": f"Bearer {TOKEN}"}
    assert client.get("/v1/head", headers=headers).status_code == 404

    response = client.post(
        "/v1/witness",
        headers=headers,
        json={
            "generation": 11,
            "state_root_sha256": _h("a"),
            "commit_hash": _h("b"),
        },
    )
    assert response.status_code == 200
    receipt = response.json()
    assert receipt["generation"] == 11
    assert receipt["witness_mode"] == REMOTE_WITNESS_MODE
    assert client.get("/v1/head", headers=headers).json() == receipt

    assessment = _verifier(private_key).assess_local_checkpoint(
        {
            "generation": 11,
            "state_root_sha256": _h("a"),
            "commit_hash": _h("b"),
        },
        receipt,
    )
    assert assessment["status"] == "PASS"
    assert assessment["external_witnessed"] is False
    assert assessment["independence_verified"] is False

    rollback = client.post(
        "/v1/witness",
        headers=headers,
        json={
            "generation": 10,
            "state_root_sha256": _h("c"),
            "commit_hash": _h("d"),
        },
    )
    assert rollback.status_code == 409
    assert rollback.json()["detail"]["code"] == "ROLLBACK_DETECTED"


def test_https_transport_requires_tls_except_explicit_loopback_qualification():
    with pytest.raises(RegistryWitnessTransportConfigError, match="requires HTTPS"):
        HttpsRegistryWitnessTransport(
            base_url="http://witness.example.test",
            bearer_token=TOKEN,
        )

    with pytest.raises(RegistryWitnessTransportConfigError, match="loopback"):
        HttpsRegistryWitnessTransport(
            base_url="http://witness.example.test",
            bearer_token=TOKEN,
            allow_insecure_loopback_for_tests=True,
        )

    transport = HttpsRegistryWitnessTransport(
        base_url="http://127.0.0.1:9999",
        bearer_token=TOKEN,
        allow_insecure_loopback_for_tests=True,
        executor=lambda _request, _timeout, _context: (404, b"{}"),
    )
    assert transport.read_head(NAMESPACE) is None


def test_https_transport_sends_auth_and_coordinates_and_maps_remote_errors():
    calls = []

    def executor(request, timeout, _context):
        calls.append((request, timeout))
        if request.full_url.endswith("/v1/head"):
            return 404, b"{}"
        body = json.loads(request.data.decode("utf-8"))
        if body["generation"] == 1:
            return (
                409,
                json.dumps(
                    {
                        "detail": {
                            "code": "ROLLBACK_DETECTED",
                            "message": "durable head is newer",
                        }
                    }
                ).encode("utf-8"),
            )
        if body["generation"] == 2:
            return (
                409,
                json.dumps(
                    {
                        "detail": {
                            "code": "WITNESS_CONFLICT",
                            "message": "same generation conflict",
                        }
                    }
                ).encode("utf-8"),
            )
        return 503, b"{}"

    transport = HttpsRegistryWitnessTransport(
        base_url="https://witness.example.test",
        bearer_token=TOKEN,
        executor=executor,
    )
    assert transport.read_head(NAMESPACE) is None
    request, timeout = calls[-1]
    assert timeout == 5.0
    assert request.get_header("Authorization") == f"Bearer {TOKEN}"

    with pytest.raises(RegistryWitnessRollbackDetected, match="durable head is newer"):
        transport.witness(
            NAMESPACE,
            RegistryWitnessCoordinates(1, _h("a"), _h("b")),
        )

    with pytest.raises(RegistryWitnessConflict, match="same generation conflict"):
        transport.witness(
            NAMESPACE,
            RegistryWitnessCoordinates(2, _h("c"), _h("d")),
        )

    with pytest.raises(RegistryWitnessUnavailable, match="unexpected HTTP status 503"):
        transport.witness(
            NAMESPACE,
            RegistryWitnessCoordinates(3, _h("e"), _h("f")),
        )
