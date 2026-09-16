import hashlib
import json

import pytest

from deployments.qcrypto_chain_testnets import verify_online


REVISION = "a" * 40


def receipt(compose_bytes: bytes, **overrides):
    data = {
        "schema": "WS-QCRYPTO-CHAIN-START-RECEIPT-V2",
        "state": "PUBLIC_TESTNET_NODES_STARTED_SYNC_NOT_YET_ATTESTED",
        "deployment_revision": REVISION,
        "compose_sha256": hashlib.sha256(compose_bytes).hexdigest(),
        "images": {
            "bitcoin_core": "example/bitcoin@sha256:" + "1" * 64,
            "ethereum_execution": "example/geth@sha256:" + "2" * 64,
            "ethereum_consensus": "example/lighthouse@sha256:" + "3" * 64,
        },
        "claims": {
            "mainnet_permitted": False,
            "live_value_authorized": False,
            "private_key_operations_permitted": False,
            "bitcoin_transaction_broadcast": False,
            "ethereum_validator_activated": False,
            "end_to_end_post_quantum_security_established": False,
        },
    }
    data.update(overrides)
    return data


def configure(monkeypatch, tmp_path, data, compose_bytes=b"services: {}\n", revision=REVISION):
    start_path = tmp_path / "start.json"
    compose_path = tmp_path / "compose.yaml"
    start_path.write_text(json.dumps(data), encoding="utf-8")
    compose_path.write_bytes(compose_bytes)
    monkeypatch.setattr(verify_online, "START_RECEIPT", start_path)
    monkeypatch.setattr(verify_online, "COMPOSE", compose_path)
    monkeypatch.setattr(verify_online, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(verify_online, "run", lambda *args, **kwargs: revision)


def test_valid_start_receipt_lineage_is_accepted(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data = receipt(compose_bytes)
    configure(monkeypatch, tmp_path, data, compose_bytes)
    loaded = verify_online.load_and_verify_start_receipt()
    assert loaded["deployment_revision"] == REVISION
    assert loaded["claims"]["mainnet_permitted"] is False


def test_stale_repository_revision_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data = receipt(compose_bytes)
    configure(monkeypatch, tmp_path, data, compose_bytes, revision="b" * 40)
    with pytest.raises(RuntimeError, match="revision changed"):
        verify_online.load_and_verify_start_receipt()


def test_changed_compose_bytes_are_rejected(monkeypatch, tmp_path):
    original = b"services: {}\n"
    data = receipt(original)
    configure(monkeypatch, tmp_path, data, b"services:\n  altered: {}\n")
    with pytest.raises(RuntimeError, match="Compose bytes changed"):
        verify_online.load_and_verify_start_receipt()


def test_missing_image_digest_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data = receipt(compose_bytes)
    data["images"]["ethereum_consensus"] = "example/lighthouse:latest"
    configure(monkeypatch, tmp_path, data, compose_bytes)
    with pytest.raises(RuntimeError, match="immutable image digest"):
        verify_online.load_and_verify_start_receipt()


def test_any_positive_execution_claim_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data = receipt(compose_bytes)
    data["claims"]["live_value_authorized"] = True
    configure(monkeypatch, tmp_path, data, compose_bytes)
    with pytest.raises(RuntimeError, match="live_value_authorized"):
        verify_online.load_and_verify_start_receipt()
