"""Installed synthetic custody fixtures used by tests and retained evidence.

This module contains no production credentials, network clients, transaction broadcast
logic, or chain-native signing.  It exists so evidence generators do not depend on the
repository's pytest package layout.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from .custody import (
    APPROVAL_CONTEXT,
    HANDOFF_SCHEMA,
    READY_HANDOFF_STATE,
    REQUEST_SCHEMA,
    EphemeralMlDsa65ReleaseSigner,
    canonical_approval_message,
    intent_sha256,
)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _sha_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_synthetic_request(
    *,
    signer=None,
    request_id: str = "CUSTODY-REQ-001",
    chain: str = "SYNTHETIC",
    network: str = "CI",
    now: datetime | None = None,
    approval_expires: datetime | None = None,
):
    now = now or datetime(2026, 9, 16, 2, 30, tzinfo=timezone.utc)
    signer = signer or EphemeralMlDsa65ReleaseSigner()
    human_private = MLDSA65PrivateKey.generate()
    human_public = human_private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
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
        "approval_id": f"APPROVAL-{request_id}",
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
        "nonce": f"approval-nonce-{request_id}-0123456789abcdef",
        "signature_b64url": "UNSIGNED",
    }
    approval["signature_b64url"] = _b64(
        human_private.sign(canonical_approval_message(approval), APPROVAL_CONTEXT)
    )
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
        "approval_key_fingerprint_sha256": hashlib.sha256(human_public).hexdigest(),
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
        "handoff_package_sha256": _sha_json(binding),
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
        "unsigned_payload_b64url": _b64(unsigned),
        "observed_network_identity_sha256": network_digest,
        "broadcast_requested": False,
        "chain_native_signing_requested": False,
    }
    return request, signer, human_public, now
