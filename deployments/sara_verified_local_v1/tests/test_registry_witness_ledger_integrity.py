from __future__ import annotations

import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.registry_monotonic_witness import RegistryWitnessCoordinates
from worldshepherd_sara.registry_witness_service import (
    RegistryWitnessLedger,
    RegistryWitnessLedgerError,
    RegistryWitnessService,
    create_registry_witness_app,
)


WITNESS_ID = "WS-MAG-1-6R-INTEGRITY"
KEY_ID = "WS-MAG-1-6R-INTEGRITY-KEY"
NAMESPACE = "worldshepherd/sara/registry-integrity"
TOKEN = "registry-witness-integrity-token-0123456789"


def _h(character: str) -> str:
    return character * 64


def _open(tmp_path, private_key):
    return RegistryWitnessLedger(
        tmp_path / "witness.db",
        private_key=private_key,
        witness_id=WITNESS_ID,
        key_id=KEY_ID,
        namespace=NAMESPACE,
    )


def _two_receipts(tmp_path, private_key):
    ledger = _open(tmp_path, private_key)
    first = ledger.witness(RegistryWitnessCoordinates(4, _h("a"), _h("b")))
    second = ledger.witness(RegistryWitnessCoordinates(8, _h("c"), _h("d")))
    return ledger, first, second


def test_integrity_report_verifies_sqlite_signature_chain_and_head(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    ledger, _first, second = _two_receipts(tmp_path, private_key)

    report = ledger.verify_integrity()

    assert report["status"] == "PASS"
    assert report["receipt_count"] == 2
    assert report["head_generation"] == 8
    assert report["head_receipt_sha256"] == second["receipt_sha256"]
    assert report["signature_chain_verified"] is True
    assert report["sqlite_integrity_verified"] is True
    assert report["external_witnessed"] is False
    assert report["independence_verified"] is False


def test_restart_rejects_deleted_chain_predecessor(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    ledger, first, _second = _two_receipts(tmp_path, private_key)

    connection = sqlite3.connect(ledger.db_path)
    try:
        connection.execute(
            "DELETE FROM witness_receipts WHERE receipt_sha256=?",
            (first["receipt_sha256"],),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RegistryWitnessLedgerError, match="hash chain is broken"):
        _open(tmp_path, private_key)


def test_restart_rejects_head_rollback_even_when_older_receipt_is_valid(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    ledger, first, _second = _two_receipts(tmp_path, private_key)

    connection = sqlite3.connect(ledger.db_path)
    try:
        connection.execute(
            "UPDATE witness_heads SET generation=?, receipt_sha256=? WHERE namespace=?",
            (4, first["receipt_sha256"], NAMESPACE),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RegistryWitnessLedgerError, match="newest receipt"):
        _open(tmp_path, private_key)


def test_restart_rejects_receipt_content_tamper(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    ledger, _first, second = _two_receipts(tmp_path, private_key)
    tampered_json = str(second).replace("'", '"').replace(_h("c"), _h("e"))

    connection = sqlite3.connect(ledger.db_path)
    try:
        connection.execute(
            "UPDATE witness_receipts SET receipt_json=? WHERE receipt_sha256=?",
            (tampered_json, second["receipt_sha256"]),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RegistryWitnessLedgerError):
        _open(tmp_path, private_key)


def test_authenticated_integrity_endpoint_reports_narrow_claim_boundary(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    ledger = _open(tmp_path, private_key)
    ledger.witness(RegistryWitnessCoordinates(2, _h("a"), _h("b")))
    service = RegistryWitnessService(ledger=ledger, service_token=TOKEN)
    client = TestClient(create_registry_witness_app(service))

    assert client.get("/v1/integrity").status_code == 401
    response = client.get(
        "/v1/integrity",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    report = response.json()
    assert report["status"] == "PASS"
    assert report["receipt_count"] == 1
    assert report["external_witnessed"] is False
    assert report["independence_verified"] is False
    assert "does not establish independent administration" in report["claims_boundary"]
