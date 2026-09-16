#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from qcrypto_external_signer import (
    CustodyError,
    CustodyIndeterminate,
    CustodyLedger,
    CustodyPolicy,
    EphemeralMlDsa65ReleaseSigner,
    ExternalCustodyService,
    FailingAfterInvocationSigner,
    verify_release_receipt,
)
from qcrypto_external_signer.custody import (
    APPROVAL_CONTEXT,
    HANDOFF_SCHEMA,
    READY_HANDOFF_STATE,
    REQUEST_SCHEMA,
    canonical_approval_message,
    intent_sha256,
)


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def sha_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def public_raw(private: MLDSA65PrivateKey) -> bytes:
    return private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def make_request(signer, human_private, now, *, request_id="CUSTODY-EVIDENCE-001"):
    human_public = public_raw(human_private)
    unsigned = b"synthetic-ci-unsigned-transaction-envelope-v1"
    network_digest = hashlib.sha256(b"SYNTHETIC:CI:network-identity-v1").hexdigest()
    destination = hashlib.sha256(b"synthetic-ci-destination-v1").hexdigest()
    review = hashlib.sha256(b"synthetic-ci-review-package-v1").hexdigest()
    intent = {
        "schema": "WS-LIVE-VALUE-EXECUTION-INTENT-V1",
        "chain": "SYNTHETIC",
        "network": "CI",
        "asset": "CI-ASSET",
        "amount_atomic": 100,
        "fee_ceiling_atomic": 10,
        "source_custody_ref": "CI-CUSTODY-REFERENCE",
        "destination_commitment_sha256": destination,
        "unsigned_transaction_digest_sha256": hashlib.sha256(unsigned).hexdigest(),
        "review_package_sha256": review,
        "production_revision": "a" * 40,
        "change_ticket_id": "CI-CHANGE-001",
        "intent_nonce": "ci-intent-nonce-0123456789abcdef",
        "valid_until": (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
    }
    digest = intent_sha256(intent)
    approval = {
        "schema": "WS-LIVE-VALUE-HUMAN-APPROVAL-V1",
        "issuer": "HUMAN_CHANGE_CONTROL",
        "approver_id": "CI-HUMAN-APPROVER",
        "approval_id": f"CI-APPROVAL-{request_id}",
        "key_id": "CI-HUMAN-MLDSA65",
        "intent_sha256": digest,
        "review_package_sha256": review,
        "destination_commitment_sha256": destination,
        "external_signer_fingerprint_sha256": signer.fingerprint_sha256,
        "network_identity_sha256": network_digest,
        "maximum_amount_atomic": 100,
        "maximum_fee_atomic": 10,
        "change_ticket_id": "CI-CHANGE-001",
        "production_revision": "a" * 40,
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "nonce": f"approval-nonce-{request_id}-0123456789abcdef",
        "signature_b64url": "UNSIGNED",
    }
    approval["signature_b64url"] = b64(human_private.sign(canonical_approval_message(approval), APPROVAL_CONTEXT))
    observed_fee = 5
    preflight = {
        "intent_sha256": digest,
        "approval_id": approval["approval_id"],
        "external_signer_fingerprint_sha256": signer.fingerprint_sha256,
        "network_identity_sha256": network_digest,
        "destination_commitment_sha256": destination,
        "observed_fee_atomic": observed_fee,
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
        "intent_sha256": digest,
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
        "observed_fee_atomic": observed_fee,
        "qcrypto_execution_authority": False,
        "qcrypto_broadcast_permitted": False,
    }
    handoff = {
        "schema": HANDOFF_SCHEMA,
        "state": READY_HANDOFF_STATE,
        "handoff_package_sha256": sha_json(binding),
        "intent_sha256": digest,
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
    return request, human_public


def svc(root, signer, human_public):
    return ExternalCustodyService(
        ledger=CustodyLedger(Path(root) / "ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"CI-HUMAN-MLDSA65": human_public},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="external-custody-evidence.json")
    args = parser.parse_args()
    now = datetime(2026, 9, 16, 2, 30, tzinfo=timezone.utc)
    human_private = MLDSA65PrivateKey.generate()

    with tempfile.TemporaryDirectory(prefix="ws-custody-evidence-") as root:
        signer = EphemeralMlDsa65ReleaseSigner()
        request, human_public = make_request(signer, human_private, now)
        first_service = svc(root, signer, human_public)
        first = first_service.execute_release(request, now=now + timedelta(seconds=1))
        retry = first_service.execute_release(deepcopy(request), now=now + timedelta(seconds=2))
        restarted = svc(root, signer, human_public).execute_release(deepcopy(request), now=now + timedelta(seconds=3))
        post_expiry = svc(root, signer, human_public).execute_release(
            deepcopy(request), now=now + timedelta(hours=1)
        )
        if not (first == retry == restarted == post_expiry):
            raise SystemExit("exact retry/restart/post-expiry retrieval did not return the persisted receipt")
        if signer.invocation_count != 1:
            raise SystemExit("custody signer was invoked more than once for an exact retry")
        if not verify_release_receipt(first, signer.public_key_bytes):
            raise SystemExit("custody release receipt did not verify")
        ledger = json.loads((Path(root) / "ledger.json").read_text())
        if ledger["requests"][request["request_id"]]["state"] != "SIGNED":
            raise SystemExit("durable custody ledger did not reach SIGNED")
        envelope_map = ledger.get("request_envelopes")
        if not isinstance(envelope_map, dict) or len(envelope_map.get(request["request_id"], "")) != 64:
            raise SystemExit("durable exact-request envelope identity was not retained")

    with tempfile.TemporaryDirectory(prefix="ws-custody-indeterminate-") as root:
        failing = FailingAfterInvocationSigner()
        bad_request, bad_human_public = make_request(
            failing, human_private, now, request_id="CUSTODY-EVIDENCE-INDETERMINATE"
        )
        bad_service = svc(root, failing, bad_human_public)
        ambiguous_blocked = False
        post_expiry_retry_blocked = False
        try:
            bad_service.execute_release(bad_request, now=now + timedelta(seconds=1))
        except CustodyIndeterminate:
            ambiguous_blocked = True
        try:
            svc(root, failing, bad_human_public).execute_release(
                deepcopy(bad_request), now=now + timedelta(hours=1)
            )
        except CustodyIndeterminate:
            post_expiry_retry_blocked = True
        bad_ledger = json.loads((Path(root) / "ledger.json").read_text())
        indeterminate_state = bad_ledger["requests"][bad_request["request_id"]]["state"]
        if not ambiguous_blocked or not post_expiry_retry_blocked or indeterminate_state != "INDETERMINATE" or failing.invocation_count != 1:
            raise SystemExit("ambiguous signer outcome was not fail-stopped across expiry")

    broadcast_blocked = False
    with tempfile.TemporaryDirectory(prefix="ws-custody-broadcast-") as root:
        signer2 = EphemeralMlDsa65ReleaseSigner()
        request2, human_public2 = make_request(signer2, human_private, now, request_id="CUSTODY-EVIDENCE-BROADCAST")
        request2["broadcast_requested"] = True
        try:
            svc(root, signer2, human_public2).execute_release(request2, now=now + timedelta(seconds=1))
        except CustodyError:
            broadcast_blocked = True
    if not broadcast_blocked:
        raise SystemExit("broadcast request was not blocked")

    evidence = {
        "schema": "WS-QCRYPTO-EXTERNAL-CUSTODY-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "EXTERNAL_CUSTODY_RELEASE_SOFTWARE_BEHAVIOR_ONLY",
        "synthetic_ci_only": True,
        "separate_trust_domain": True,
        "sara_runtime_dependency": False,
        "receipt": first,
        "receipt_verified": True,
        "exact_retry_identical": first == retry,
        "restart_retry_identical": first == restarted,
        "post_expiry_retry_identical": first == post_expiry,
        "signer_invocation_count": signer.invocation_count,
        "durable_signed_state": ledger["requests"][request["request_id"]]["state"],
        "durable_request_envelope_identity": True,
        "ambiguous_outcome_state": indeterminate_state,
        "ambiguous_outcome_post_expiry_retry_blocked": post_expiry_retry_blocked,
        "ambiguous_signer_invocation_count": failing.invocation_count,
        "broadcast_request_blocked": broadcast_blocked,
        "mainnet_permitted": False,
        "transaction_broadcast": False,
        "chain_native_transaction_signature": False,
        "real_wallet_used": False,
        "real_value_moved": False,
        "private_key_exported": False,
        "production_hsm_integrated": False,
        "end_to_end_pq_security_established": False,
        "claims_boundary": (
            "Synthetic CI proof of a separately controlled ML-DSA-65 custody-release attestation only. "
            "No real wallet, native chain transaction signature, broadcast, mainnet authorization, real value movement, "
            "production HSM integration, or end-to-end post-quantum cryptocurrency security is established."
        ),
    }
    evidence["evidence_sha256"] = sha_json(evidence)
    Path(args.output).write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("external_custody_status: PASS")
    print("receipt_sha256:", first["receipt_sha256"])
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
