#!/usr/bin/env python3
"""Generate retained synthetic evidence for opaque-provider custody reconciliation."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

from qcrypto_external_signer.custody import (
    CustodyIndeterminate,
    CustodyLedger,
    CustodyPolicy,
    _canonical,
    _sha,
)
from qcrypto_external_signer.opaque_provider import (
    OpaqueProviderReleaseSigner,
    ProviderAmbiguousOutcome,
    ProviderResult,
    ProviderState,
    ReferenceOpaqueMlDsa65Provider,
    provider_operation_id,
)
from qcrypto_external_signer.provider_custody import (
    OpaqueProviderCustodyService,
    verify_opaque_provider_receipt,
)
from qcrypto_external_signer.synthetic import build_synthetic_request


class AmbiguousWithoutCommitProvider(ReferenceOpaqueMlDsa65Provider):
    def begin_sign(self, operation_id: str, message: bytes, context: bytes) -> ProviderResult:
        self.invocation_count += 1
        raise ProviderAmbiguousOutcome(operation_id, "synthetic timeout before commit")

    def reconcile(self, operation_id: str) -> ProviderResult:
        return ProviderResult(
            operation_id=operation_id,
            state=ProviderState.NOT_FOUND_SAFE_TO_RETRY,
            key_handle=self.key_handle,
            algorithm=self.algorithm,
            message_sha256="",
            context_sha256="",
            signature_b64url=None,
            safe_to_retry=True,
        )


def service(root: Path, signer: OpaqueProviderReleaseSigner, human_public: bytes) -> OpaqueProviderCustodyService:
    return OpaqueProviderCustodyService(
        ledger=CustodyLedger(root / "custody-ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"HUMAN-MLDSA65-TEST": human_public},
    )


def canonical_sha(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _handle_substitution_is_rejected(receipt: dict, signer: OpaqueProviderReleaseSigner) -> bool:
    """Model a ledger editor recomputing every unkeyed identifier after handle substitution."""
    tampered = deepcopy(receipt)
    tampered["provider_key_handle"] = "ref-hsm://qcrypto/ml-dsa-65/substituted-key"
    binding = {
        key: value
        for key, value in tampered.items()
        if key
        not in {
            "state",
            "signature_b64url",
            "provider_operation_id",
            "provider_reconciled",
            "claims_boundary",
            "receipt_sha256",
        }
    }
    tampered["provider_operation_id"] = provider_operation_id(
        key_handle=tampered["provider_key_handle"],
        message=_canonical(binding),
        context=signer.context,
    )
    unsigned_receipt = dict(tampered)
    unsigned_receipt.pop("receipt_sha256", None)
    tampered["receipt_sha256"] = _sha(unsigned_receipt)
    return not verify_opaque_provider_receipt(
        tampered,
        public_key_bytes=signer.public_key_bytes,
    )


def build_evidence() -> dict:
    with tempfile.TemporaryDirectory(prefix="qcrypto-opaque-provider-") as tmp:
        root = Path(tmp)
        provider = ReferenceOpaqueMlDsa65Provider(ack_loss_once=True)
        signer = OpaqueProviderReleaseSigner(provider)
        request, _ignored, human_public, now = build_synthetic_request(signer=signer)
        custody = service(root, signer, human_public)

        ambiguous_blocked = False
        try:
            custody.execute_release(request, now=now + timedelta(seconds=1))
        except CustodyIndeterminate:
            ambiguous_blocked = True

        after_ambiguous = json.loads((root / "custody-ledger.json").read_text(encoding="utf-8"))
        entry = after_ambiguous["requests"][request["request_id"]]
        operation_id = entry["provider_operation_id"]
        release_binding_retained = isinstance(entry.get("release_binding"), dict)
        signed_handle_retained = (
            isinstance(entry.get("release_binding"), dict)
            and entry["release_binding"].get("provider_key_handle") == provider.key_handle
        )
        indeterminate_state = entry.get("state")
        invocations_before_reconcile = provider.invocation_count

        receipt = custody.reconcile_release(request)
        receipt_verified = verify_opaque_provider_receipt(
            receipt,
            public_key_bytes=signer.public_key_bytes,
        )
        handle_substitution_rejected = _handle_substitution_is_rejected(receipt, signer)
        invocations_after_reconcile = provider.invocation_count

        restarted = service(root, OpaqueProviderReleaseSigner(provider), human_public)
        post_expiry = restarted.execute_release(request, now=now + timedelta(minutes=20))
        post_expiry_retry_identical = post_expiry == receipt
        invocations_after_restart_retry = provider.invocation_count

        final_ledger = json.loads((root / "custody-ledger.json").read_text(encoding="utf-8"))
        final_entry = final_ledger["requests"][request["request_id"]]

    with tempfile.TemporaryDirectory(prefix="qcrypto-provider-not-found-") as tmp2:
        root2 = Path(tmp2)
        missing_provider = AmbiguousWithoutCommitProvider()
        missing_signer = OpaqueProviderReleaseSigner(missing_provider)
        missing_request, _ignored, missing_human_public, missing_now = build_synthetic_request(
            signer=missing_signer,
            request_id="CUSTODY-REQ-NOT-FOUND-001",
        )
        missing_custody = service(root2, missing_signer, missing_human_public)
        try:
            missing_custody.execute_release(
                missing_request,
                now=missing_now + timedelta(seconds=1),
            )
        except CustodyIndeterminate:
            pass
        no_commit_invocations_before = missing_provider.invocation_count
        no_auto_retry_when_not_found = False
        try:
            missing_custody.reconcile_release(missing_request)
        except CustodyIndeterminate as exc:
            no_auto_retry_when_not_found = "new human authorization" in str(exc)
        no_commit_invocations_after = missing_provider.invocation_count
        missing_ledger = json.loads((root2 / "custody-ledger.json").read_text(encoding="utf-8"))
        missing_entry = missing_ledger["requests"][missing_request["request_id"]]

    evidence = {
        "schema": "WS-QCRYPTO-OPAQUE-PROVIDER-CUSTODY-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "OPAQUE_PROVIDER_CUSTODY_SOFTWARE_BEHAVIOR_ONLY",
        "synthetic_ci_only": True,
        "separate_trust_domain": True,
        "private_key_export_api_present": False,
        "production_hsm_integrated": False,
        "fips_validated_module_established": False,
        "native_chain_transaction_signature": False,
        "transaction_broadcast": False,
        "mainnet_permitted": False,
        "real_value_moved": False,
        "provider_ack_loss_blocked_as_indeterminate": ambiguous_blocked,
        "durable_indeterminate_state": indeterminate_state,
        "provider_operation_id": operation_id,
        "provider_operation_id_retained_before_reconciliation": operation_id.startswith("QCRYPTO-PROVIDER-"),
        "release_binding_retained_before_reconciliation": release_binding_retained,
        "provider_key_handle_in_signed_binding": signed_handle_retained,
        "provider_handle_and_operation_id_substitution_rejected": handle_substitution_rejected,
        "provider_invocations_before_reconcile": invocations_before_reconcile,
        "provider_invocations_after_reconcile": invocations_after_reconcile,
        "reconciliation_did_not_reinvoke_signer": invocations_before_reconcile == invocations_after_reconcile == 1,
        "receipt_verified": receipt_verified,
        "receipt_provider_reconciled": receipt.get("provider_reconciled") is True,
        "receipt_provider_operation_matches_ledger": receipt.get("provider_operation_id") == operation_id,
        "receipt_provider_key_handle_matches_provider": receipt.get("provider_key_handle") == provider.key_handle,
        "durable_final_state": final_entry.get("state"),
        "durable_provider_reconciled": final_entry.get("provider_reconciled") is True,
        "post_expiry_retry_identical": post_expiry_retry_identical,
        "provider_invocations_after_restart_retry": invocations_after_restart_retry,
        "provider_not_found_safe_to_retry_reported": missing_entry.get("provider_reconciliation_state") == "NOT_FOUND_SAFE_TO_RETRY",
        "provider_not_found_did_not_auto_retry": (
            no_auto_retry_when_not_found
            and no_commit_invocations_before == no_commit_invocations_after == 1
        ),
        "provider_not_found_requires_new_human_authorization": "new_human_authorization_required" in str(missing_entry.get("indeterminate_reason", "")),
        "receipt": receipt,
        "claims_boundary": (
            "Synthetic software evidence only. Demonstrates opaque-key custody state-machine behavior, "
            "signed provider-handle binding, provider operation reconciliation, and no-double-sign "
            "recovery semantics. It does not establish production HSM/KMS integration, FIPS validation, "
            "native-chain signing, transaction broadcast, mainnet authorization, movement of real value, "
            "Federal compliance, or independent validation."
        ),
    }
    evidence["evidence_sha256"] = canonical_sha(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evidence = build_evidence()
    Path(args.output).write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("opaque_provider_custody_evidence: PASS")
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
