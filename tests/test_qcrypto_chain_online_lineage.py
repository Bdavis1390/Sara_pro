import hashlib
import json

import pytest

from deployments.qcrypto_chain_testnets import verify_online


REVISION = "a" * 40
CONFIGURED_URL = "https://hoodi.checkpoint.sigp.io"
ROOT_A = "0x" + "a" * 64
AGREEING = ["sigma_prime", "ethpandaops"]


def canonical_json_bytes(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")


def quorum_receipt(**overrides):
    data = {
        "schema": "WS-QCRYPTO-HOODI-CHECKPOINT-QUORUM-V1",
        "state": "HOODI_CHECKPOINT_QUORUM_ACCEPTED",
        "accepted": True,
        "configured_url": CONFIGURED_URL,
        "quorum_root": ROOT_A,
        "quorum_count": 2,
        "provider_count": 3,
        "agreeing_providers": AGREEING,
        "consensus_verification_replaced": False,
        "network": "HOODI",
        "chain_id": 560048,
    }
    data.update(overrides)
    return data


def receipt(compose_bytes: bytes, quorum_bytes: bytes, **overrides):
    data = {
        "schema": "WS-QCRYPTO-CHAIN-START-RECEIPT-V3",
        "state": "PUBLIC_TESTNET_NODES_STARTED_SYNC_NOT_YET_ATTESTED",
        "deployment_revision": REVISION,
        "compose_sha256": hashlib.sha256(compose_bytes).hexdigest(),
        "images": {
            "bitcoin_core": "example/bitcoin@sha256:" + "1" * 64,
            "ethereum_execution": "example/geth@sha256:" + "2" * 64,
            "ethereum_consensus": "example/lighthouse@sha256:" + "3" * 64,
        },
        "hoodi_checkpoint_bootstrap": {
            "configured_url": CONFIGURED_URL,
            "quorum_root": ROOT_A,
            "agreeing_providers": AGREEING,
            "quorum_count": 2,
            "provider_count": 3,
            "quorum_receipt_sha256": hashlib.sha256(quorum_bytes).hexdigest(),
            "consensus_verification_replaced": False,
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


def configure(
    monkeypatch,
    tmp_path,
    data,
    compose_bytes=b"services: {}\n",
    quorum_data=None,
    revision=REVISION,
):
    start_path = tmp_path / "start.json"
    compose_path = tmp_path / "compose.yaml"
    checkpoint_path = tmp_path / "checkpoint.json"
    start_path.write_text(json.dumps(data), encoding="utf-8")
    compose_path.write_bytes(compose_bytes)
    checkpoint_path.write_bytes(canonical_json_bytes(quorum_data or quorum_receipt()))
    monkeypatch.setattr(verify_online, "START_RECEIPT", start_path)
    monkeypatch.setattr(verify_online, "COMPOSE", compose_path)
    monkeypatch.setattr(verify_online, "CHECKPOINT_RECEIPT", checkpoint_path)
    monkeypatch.setattr(verify_online, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(verify_online, "run", lambda *args, **kwargs: revision)
    return checkpoint_path


def valid_fixture(compose_bytes=b"services: {}\n"):
    quorum = quorum_receipt()
    quorum_bytes = canonical_json_bytes(quorum)
    return receipt(compose_bytes, quorum_bytes), quorum


def test_geth_protocol_snapshot_accepts_hoodi_identity():
    text = "noise\n" + json.dumps(
        {
            "network": 560048,
            "genesis": verify_online.HOODI_GENESIS_HASH,
            "blockNumber": 42,
        }
    )
    network_id, genesis_hash, block_number = verify_online.parse_geth_protocol_snapshot(text)
    assert network_id == 560048
    assert genesis_hash == verify_online.HOODI_GENESIS_HASH
    assert block_number == 42


def test_geth_protocol_snapshot_rejects_wrong_network():
    text = json.dumps(
        {
            "network": 1,
            "genesis": verify_online.HOODI_GENESIS_HASH,
            "blockNumber": 0,
        }
    )
    with pytest.raises(RuntimeError, match="network id mismatch"):
        verify_online.parse_geth_protocol_snapshot(text)


def test_geth_protocol_snapshot_rejects_wrong_genesis():
    text = json.dumps(
        {
            "network": 560048,
            "genesis": "0x" + "0" * 64,
            "blockNumber": 0,
        }
    )
    with pytest.raises(RuntimeError, match="genesis hash mismatch"):
        verify_online.parse_geth_protocol_snapshot(text)


def test_valid_v3_start_receipt_lineage_is_accepted(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data, quorum = valid_fixture(compose_bytes)
    configure(monkeypatch, tmp_path, data, compose_bytes, quorum)
    loaded = verify_online.load_and_verify_start_receipt()
    assert loaded["deployment_revision"] == REVISION
    assert loaded["hoodi_checkpoint_bootstrap"]["quorum_root"] == ROOT_A
    assert loaded["claims"]["mainnet_permitted"] is False


def test_stale_repository_revision_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data, quorum = valid_fixture(compose_bytes)
    configure(monkeypatch, tmp_path, data, compose_bytes, quorum, revision="b" * 40)
    with pytest.raises(RuntimeError, match="revision changed"):
        verify_online.load_and_verify_start_receipt()


def test_changed_compose_bytes_are_rejected(monkeypatch, tmp_path):
    original = b"services: {}\n"
    data, quorum = valid_fixture(original)
    configure(monkeypatch, tmp_path, data, b"services:\n  altered: {}\n", quorum)
    with pytest.raises(RuntimeError, match="Compose bytes changed"):
        verify_online.load_and_verify_start_receipt()


def test_missing_image_digest_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data, quorum = valid_fixture(compose_bytes)
    data["images"]["ethereum_consensus"] = "example/lighthouse:latest"
    configure(monkeypatch, tmp_path, data, compose_bytes, quorum)
    with pytest.raises(RuntimeError, match="immutable image digest"):
        verify_online.load_and_verify_start_receipt()


def test_checkpoint_receipt_tampering_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data, quorum = valid_fixture(compose_bytes)
    checkpoint_path = configure(monkeypatch, tmp_path, data, compose_bytes, quorum)
    altered = quorum_receipt(quorum_root="0x" + "b" * 64)
    checkpoint_path.write_bytes(canonical_json_bytes(altered))
    with pytest.raises(RuntimeError, match="receipt changed"):
        verify_online.load_and_verify_start_receipt()


def test_checkpoint_root_mismatch_is_rejected_even_with_matching_digest(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    quorum = quorum_receipt(quorum_root="0x" + "b" * 64)
    quorum_bytes = canonical_json_bytes(quorum)
    data = receipt(compose_bytes, quorum_bytes)
    configure(monkeypatch, tmp_path, data, compose_bytes, quorum)
    with pytest.raises(RuntimeError, match="finalized-root quorum changed"):
        verify_online.load_and_verify_start_receipt()


def test_checkpoint_provider_set_mismatch_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    quorum = quorum_receipt(agreeing_providers=["sigma_prime", "ethstaker"])
    quorum_bytes = canonical_json_bytes(quorum)
    data = receipt(compose_bytes, quorum_bytes)
    configure(monkeypatch, tmp_path, data, compose_bytes, quorum)
    with pytest.raises(RuntimeError, match="provider set changed"):
        verify_online.load_and_verify_start_receipt()


def test_any_positive_execution_claim_is_rejected(monkeypatch, tmp_path):
    compose_bytes = b"services: {}\n"
    data, quorum = valid_fixture(compose_bytes)
    data["claims"]["live_value_authorized"] = True
    configure(monkeypatch, tmp_path, data, compose_bytes, quorum)
    with pytest.raises(RuntimeError, match="live_value_authorized"):
        verify_online.load_and_verify_start_receipt()
