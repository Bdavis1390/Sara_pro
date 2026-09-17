from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from qcrypto_external_signer.custody import (
    APPROVAL_CONTEXT,
    HANDOFF_SCHEMA,
    READY_HANDOFF_STATE,
    REQUEST_SCHEMA,
    CustodyConflict,
    CustodyError,
    CustodyIndeterminate,
    CustodyLedger,
    CustodyPolicy,
    EphemeralMlDsa65ReleaseSigner,
    ExternalCustodyService,
    FailingAfterInvocationSigner,
    canonical_approval_message,
    intent_sha256,
    verify_release_receipt,
)


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def sha_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def raw_public(private: MLDSA65PrivateKey) -> bytes:
    return private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def fixture(
    *,
    signer=None,
    request_id="CUSTODY-REQ-001",
    chain="SYNTHETIC",
    network="CI",
    now=None,
    approval_expires=None,
):
    now = now or datetime(2026, 9, 16, 2, 30, tzinfo=timezone.utc)
    signer = signer or EphemeralMlDsa65ReleaseSigner()
    human_private = MLDSA65PrivateKey.generate()
    human_public = raw_public(human_private)
    unsigned = b"synthetic-unsigned-value-intent-v1"
    network_digest = hashlib.sha256(f"{chain}:{network}:identity-v1".encode()).hexdigest()
    destination = hashlib.sha256(b"synthetic-destination-v1").hexdigest()
    review = hashlib.sha256(b"review-package-v1").hexdigest()
    intent = {
        "schema": "WS-LIVE-VALUE-EXECUTION-INTENT-V1",
        "chain": chain,
        "network": network,
        "asset": "TEST-ASSET",
        "amount_atomic": 100,
        "fee_ceiling_atomic": 10,
        "source_custody_ref": "CUSTODY-TEST-001",
        "destination_commitment_sha256": destination,
        "unsigned_transaction_digest_sha256": hashlib.sha256(unsigned).hexdigest(),
        "review_package_sha256": review,
        "production_revision": "a" * 40,
        "change_ticket_id": "CHANGE-TEST-001",
        "intent_nonce": "intent-nonce-0123456789abcdef",
        "valid_until": (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
    }
    intent_digest = intent_sha256(intent)
    approval = {
        "schema": "WS-LIVE-VALUE-HUMAN-APPROVAL-V1",
        "issuer": "HUMAN_CHANGE_CONTROL",
        "approver_id": "HUMAN-REVIEWER-TEST",
        "approval_id": "APPROVAL-TEST-001",
        "key_id": "HUMAN-MLDSA65-TEST",
        "intent_sha256": intent_digest,
        "review_package_sha256": review,
        "destination_commitment_sha256": destination,
        "external_signer_fingerprint_sha256": signer.fingerprint_sha256,
        "network_identity_sha256": network_digest,
        "maximum_amount_atomic": 100,
        "maximum_fee_atomic": 10,
        "change_ticket_id": "CHANGE-TEST-001",
        "production_revision": "a" * 40,
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (approval_expires or now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "nonce": "approval-nonce-0123456789abcdef",
        "signature_b64url": "UNSIGNED",
    }
    signature = human_private.sign(canonical_approval_message(approval), APPROVAL_CONTEXT)
    approval["signature_b64url"] = b64(signature)
    human_fingerprint = hashlib.sha256(human_public).hexdigest()
    preflight = {
        "intent_sha256": intent_digest,
        "approval_id": approval["approval_id"],
        "external_signer_fingerprint_sha256": signer.fingerprint_sha256,
        "network_identity_sha256": network_digest,
        "destination_commitment_sha256": destination,
        "observed_fee_atomic": 5,
        "destination_allowlist_match": True,
        "balance_or_utxo_sufficient": True,
        "nonce_or_outpoint_reserved": True,
        "simulation_or_policy_check_passed": True,
        "monitoring_ready": True,
        "pause_ready": True,
        "rollback_ready": True,
        "approval_consumed": False,
        "signed_payload_present": False,
        "private_key_material_present": False,
        "broadcast_requested": False,
    }
    binding = {
        "schema": HANDOFF_SCHEMA,
        "intent_sha256": intent_digest,
        "approval_id": approval["approval_id"],
        "approver_id": approval["approver_id"],
        "approval_key_fingerprint_sha256": human_fingerprint,
        "external_signer_fingerprint_sha256": signer.fingerprint_sha256,
        "network_identity_sha256": network_digest,
        "destination_commitment_sha256": destination,
        "unsigned_transaction_digest_sha256": intent["unsigned_transaction_digest_sha256"],
        "review_package_sha256": review,
        "production_revision": intent["production_revision"],
        "change_ticket_id": intent["change_ticket_id"],
        "amount_atomic": 100,
        "fee_ceiling_atomic": 10,
        "observed_fee_atomic": 5,
        "qcrypto_execution_authority": False,
        "qcrypto_broadcast_permitted": False,
    }
    handoff = {
        "schema": HANDOFF_SCHEMA,
        "state": READY_HANDOFF_STATE,
        "handoff_package_sha256": sha_json(binding),
        "intent_sha256": intent_digest,
        "approval_id": approval["approval_id"],
        "approver_id": approval["approver_id"],
        "human_live_value_approval_verified": True,
        "external_signer_handoff_ready": True,
        "point_of_value_moving_execution_reached": True,
        "qcrypto_execution_authority": False,
        "qcrypto_live_value_authorized": False,
        "qcrypto_private_key_operations_permitted": False,
        "qcrypto_broadcast_permitted": False,
    }
    request = {
        "schema": REQUEST_SCHEMA,
        "request_id": request_id,
        "intent": intent,
        "human_approval": approval,
        "handoff": handoff,
        "preflight": preflight,
        "unsigned_payload_b64url": b64(unsigned),
        "observed_network_identity_sha256": network_digest,
        "broadcast_requested": False,
        "chain_native_signing_requested": False,
    }
    return request, signer, human_public, now


def service(tmp_path, signer, human_public):
    return ExternalCustodyService(
        ledger=CustodyLedger(tmp_path / "custody-ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"HUMAN-MLDSA65-TEST": human_public},
    )


def test_happy_path_produces_verifiable_custody_release_not_native_transaction_signature(tmp_path):
    request, signer, human_public, now = fixture()
    receipt = service(tmp_path, signer, human_public).execute_release(request, now=now + timedelta(seconds=1))
    assert receipt["state"] == "SIGNED_CUSTODY_RELEASE_ATTESTATION"
    assert receipt["chain_native_transaction_signature"] is False
    assert receipt["transaction_broadcast"] is False
    assert receipt["real_value_moved"] is False
    assert receipt["mainnet"] is False
    assert receipt["production_hsm_integrated"] is False
    assert verify_release_receipt(receipt, signer.public_key_bytes) is True
    assert signer.invocation_count == 1


def test_exact_retry_is_idempotent_and_does_not_sign_twice(tmp_path):
    request, signer, human_public, now = fixture()
    svc = service(tmp_path, signer, human_public)
    first = svc.execute_release(request, now=now + timedelta(seconds=1))
    second = svc.execute_release(deepcopy(request), now=now + timedelta(seconds=2))
    assert first == second
    assert signer.invocation_count == 1


def test_restart_retry_returns_persisted_receipt(tmp_path):
    request, signer, human_public, now = fixture()
    first = service(tmp_path, signer, human_public).execute_release(request, now=now + timedelta(seconds=1))
    second = service(tmp_path, signer, human_public).execute_release(request, now=now + timedelta(seconds=2))
    assert second == first
    assert signer.invocation_count == 1


def test_same_request_id_changed_valid_content_conflicts(tmp_path):
    request, signer, human_public, now = fixture()
    svc = service(tmp_path, signer, human_public)
    svc.execute_release(request, now=now + timedelta(seconds=1))
    changed = deepcopy(request)
    changed["preflight"]["observed_fee_atomic"] = 6
    # The handoff package must also change for this alternate valid preflight.
    approval = changed["human_approval"]
    intent = changed["intent"]
    binding = {
        "schema": HANDOFF_SCHEMA,
        "intent_sha256": intent_sha256(intent),
        "approval_id": approval["approval_id"],
        "approver_id": approval["approver_id"],
        "approval_key_fingerprint_sha256": hashlib.sha256(human_public).hexdigest(),
        "external_signer_fingerprint_sha256": signer.fingerprint_sha256,
        "network_identity_sha256": approval["network_identity_sha256"],
        "destination_commitment_sha256": intent["destination_commitment_sha256"],
        "unsigned_transaction_digest_sha256": intent["unsigned_transaction_digest_sha256"],
        "review_package_sha256": intent["review_package_sha256"],
        "production_revision": intent["production_revision"],
        "change_ticket_id": intent["change_ticket_id"],
        "amount_atomic": intent["amount_atomic"],
        "fee_ceiling_atomic": intent["fee_ceiling_atomic"],
        "observed_fee_atomic": 6,
        "qcrypto_execution_authority": False,
        "qcrypto_broadcast_permitted": False,
    }
    changed["handoff"]["handoff_package_sha256"] = sha_json(binding)
    with pytest.raises(CustodyConflict, match="request_id"):
        svc.execute_release(changed, now=now + timedelta(seconds=2))


def test_same_approval_cannot_authorize_second_request_id(tmp_path):
    request, signer, human_public, now = fixture()
    svc = service(tmp_path, signer, human_public)
    svc.execute_release(request, now=now + timedelta(seconds=1))
    replay = deepcopy(request)
    replay["request_id"] = "CUSTODY-REQ-002"
    with pytest.raises(CustodyConflict, match="approval_id"):
        svc.execute_release(replay, now=now + timedelta(seconds=2))


def test_wrong_signer_fingerprint_is_blocked(tmp_path):
    request, _approved_signer, human_public, now = fixture()
    wrong = EphemeralMlDsa65ReleaseSigner()
    with pytest.raises(CustodyError, match="approved"):
        service(tmp_path, wrong, human_public).execute_release(request, now=now + timedelta(seconds=1))


def test_mainnet_is_not_in_first_tranche_allowlist(tmp_path):
    request, signer, human_public, now = fixture(chain="BITCOIN", network="MAINNET")
    with pytest.raises(CustodyError, match="allowlist|mainnet"):
        service(tmp_path, signer, human_public).execute_release(request, now=now + timedelta(seconds=1))


@pytest.mark.parametrize("field", ["broadcast_requested", "chain_native_signing_requested"])
def test_broadcast_and_native_transaction_signing_requests_are_blocked(tmp_path, field):
    request, signer, human_public, now = fixture()
    request[field] = True
    with pytest.raises(CustodyError):
        service(tmp_path, signer, human_public).execute_release(request, now=now + timedelta(seconds=1))


def test_unsigned_payload_digest_mismatch_is_blocked(tmp_path):
    request, signer, human_public, now = fixture()
    request["unsigned_payload_b64url"] = b64(b"different-payload")
    with pytest.raises(CustodyError, match="unsigned payload digest"):
        service(tmp_path, signer, human_public).execute_release(request, now=now + timedelta(seconds=1))


def test_ambiguous_signer_outcome_becomes_indeterminate_and_cannot_auto_retry(tmp_path):
    signer = FailingAfterInvocationSigner()
    request, signer, human_public, now = fixture(signer=signer)
    svc = service(tmp_path, signer, human_public)
    with pytest.raises(CustodyIndeterminate, match="indeterminate"):
        svc.execute_release(request, now=now + timedelta(seconds=1))
    assert signer.invocation_count == 1
    with pytest.raises(CustodyIndeterminate, match="indeterminate"):
        svc.execute_release(request, now=now + timedelta(seconds=2))
    assert signer.invocation_count == 1


def test_receipt_and_ledger_do_not_contain_private_key_material(tmp_path):
    request, signer, human_public, now = fixture()
    receipt = service(tmp_path, signer, human_public).execute_release(request, now=now + timedelta(seconds=1))
    text = json.dumps(receipt, sort_keys=True).lower() + (tmp_path / "custody-ledger.json").read_text().lower()
    assert "private_key" not in text
    assert "seed phrase" not in text
    assert "mnemonic" not in text
