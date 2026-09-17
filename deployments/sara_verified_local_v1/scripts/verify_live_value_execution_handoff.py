#!/usr/bin/env python3
"""Generate synthetic CI evidence for the last boundary before value execution.

No real wallet, account, destination, private key, transaction, or fund is used.
The generated ML-DSA key signs only the synthetic human-approval fixture and is
held in memory for this process.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from worldshepherd_sara.live_value_execution_handoff import (
    HUMAN_APPROVAL_CONTEXT,
    ExternalExecutionPreflight,
    HumanLiveValueApproval,
    HumanLiveValueApprovalVerifier,
    LiveValueExecutionIntent,
    assess_live_value_execution_handoff,
    canonical_human_approval_message,
    execution_intent_sha256,
)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="live-value-execution-handoff-evidence.json")
    args = parser.parse_args()

    now = datetime(2026, 9, 16, 2, 30, tzinfo=timezone.utc)
    human_key = MLDSA65PrivateKey.generate()
    human_public = human_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )

    intent = LiveValueExecutionIntent(
        chain="SYNTHETIC-CI-CANARY",
        network="NO-REAL-NETWORK",
        asset="TEST-UNIT",
        amount_atomic=1,
        fee_ceiling_atomic=1,
        source_custody_ref="synthetic-ci-only",
        destination_commitment_sha256="1" * 64,
        unsigned_transaction_digest_sha256="2" * 64,
        review_package_sha256="3" * 64,
        production_revision="4" * 40,
        change_ticket_id="CI-LVC-HANDOFF-001",
        intent_nonce="synthetic-intent-0001",
        valid_until=now + timedelta(minutes=10),
    )
    unsigned_approval = HumanLiveValueApproval(
        approver_id="SYNTHETIC-CI-APPROVER",
        approval_id="SYNTHETIC-CI-APPROVAL-001",
        key_id="synthetic-human-approval-key",
        intent_sha256=execution_intent_sha256(intent),
        review_package_sha256=intent.review_package_sha256,
        destination_commitment_sha256=intent.destination_commitment_sha256,
        external_signer_fingerprint_sha256="5" * 64,
        network_identity_sha256="6" * 64,
        maximum_amount_atomic=1,
        maximum_fee_atomic=1,
        change_ticket_id=intent.change_ticket_id,
        production_revision=intent.production_revision,
        issued_at=now - timedelta(seconds=5),
        expires_at=now + timedelta(minutes=5),
        nonce="synthetic-approval-0001",
        signature_b64url="UNSIGNED",
    )
    approval = unsigned_approval.model_copy(
        update={
            "signature_b64url": b64url(
                human_key.sign(
                    canonical_human_approval_message(unsigned_approval),
                    HUMAN_APPROVAL_CONTEXT,
                )
            )
        }
    )
    verifier = HumanLiveValueApprovalVerifier(
        public_keys_b64url={"synthetic-human-approval-key": b64url(human_public)}
    )
    verified = verifier.verify(approval, intent, now=now)

    preflight = ExternalExecutionPreflight(
        intent_sha256=execution_intent_sha256(intent),
        approval_id=verified.approval_id,
        external_signer_fingerprint_sha256=verified.external_signer_fingerprint_sha256,
        network_identity_sha256=verified.network_identity_sha256,
        destination_commitment_sha256=intent.destination_commitment_sha256,
        observed_fee_atomic=1,
        destination_allowlist_match=True,
        balance_or_utxo_sufficient=True,
        nonce_or_outpoint_reserved=True,
        simulation_or_policy_check_passed=True,
        monitoring_ready=True,
        pause_ready=True,
        rollback_ready=True,
    )

    ready = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=preflight,
    )
    broadcast_blocked = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=replace(preflight, broadcast_requested=True),
    )
    replay_blocked = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=replace(preflight, approval_consumed=True),
    )
    signer_mismatch_blocked = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=replace(preflight, external_signer_fingerprint_sha256="7" * 64),
    )

    if not ready.external_signer_handoff_ready:
        raise SystemExit("synthetic complete handoff did not reach external signer boundary")
    if any(
        result.external_signer_handoff_ready
        for result in (broadcast_blocked, replay_blocked, signer_mismatch_blocked)
    ):
        raise SystemExit("negative control improperly reached external signer boundary")

    evidence = {
        "schema": "WS-LIVE-VALUE-EXECUTION-HANDOFF-EVIDENCE-V1",
        "status": "PASS",
        "synthetic_ci_only": True,
        "real_wallet_used": False,
        "real_destination_used": False,
        "real_network_used": False,
        "real_value_moved": False,
        "private_key_exported": False,
        "signed_transaction_created": False,
        "transaction_broadcast": False,
        "human_approval_scheme": "ML-DSA-65",
        "human_approval_context": HUMAN_APPROVAL_CONTEXT.decode("ascii"),
        "intent_sha256": execution_intent_sha256(intent),
        "unsigned_transaction_digest_sha256": intent.unsigned_transaction_digest_sha256,
        "handoff": ready.to_dict(),
        "negative_controls": {
            "broadcast_request_blocked": broadcast_blocked.to_dict(),
            "consumed_approval_replay_blocked": replay_blocked.to_dict(),
            "signer_mismatch_blocked": signer_mismatch_blocked.to_dict(),
        },
        "claims_boundary": (
            "Synthetic CI evidence only. It proves bounded software behavior up to the external-signer handoff boundary; "
            "it does not record a real human live-value approval, create a signed transaction, broadcast a transaction, "
            "move value, grant QCRYPTO execution authority, or establish production deployment readiness."
        ),
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    evidence["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("live_value_execution_handoff_status: PASS")
    print("state:", ready.state)
    print("handoff_package_sha256:", ready.handoff_package_sha256)
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
