from __future__ import annotations

import json
from copy import deepcopy
from datetime import timedelta

import pytest

from qcrypto_external_signer.custody import (
    CustodyConflict,
    CustodyIndeterminate,
    CustodyLedger,
    CustodyPolicy,
)
from qcrypto_external_signer.opaque_provider import (
    OpaqueProviderReleaseSigner,
    ProviderAmbiguousOutcome,
    ProviderResult,
    ProviderState,
    ReferenceOpaqueMlDsa65Provider,
)
from qcrypto_external_signer.provider_custody import (
    OpaqueProviderCustodyService,
    verify_opaque_provider_receipt,
)
from tests.test_custody import fixture


def opaque_service(tmp_path, signer, human_public):
    return OpaqueProviderCustodyService(
        ledger=CustodyLedger(tmp_path / "custody-ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"HUMAN-MLDSA65-TEST": human_public},
    )


def test_ack_loss_reconciles_after_expiry_without_second_signer_invocation(tmp_path):
    provider = ReferenceOpaqueMlDsa65Provider(ack_loss_once=True)
    signer = OpaqueProviderReleaseSigner(provider)
    request, _signer, human_public, now = fixture(signer=signer)
    svc = opaque_service(tmp_path, signer, human_public)

    with pytest.raises(CustodyIndeterminate, match="reconcile"):
        svc.execute_release(request, now=now + timedelta(seconds=1))
    assert provider.invocation_count == 1

    ledger = json.loads((tmp_path / "custody-ledger.json").read_text(encoding="utf-8"))
    entry = ledger["requests"][request["request_id"]]
    assert entry["state"] == "INDETERMINATE"
    assert entry["provider_operation_id"].startswith("QCRYPTO-PROVIDER-")
    assert isinstance(entry["release_binding"], dict)
    assert "signature_b64url" not in entry

    # Reconciliation is recovery of the already-invoked provider operation, so it
    # remains valid after both the five-minute approval and ten-minute intent expire.
    receipt = svc.reconcile_release(request)
    assert receipt["provider_reconciled"] is True
    assert receipt["provider_operation_id"] == entry["provider_operation_id"]
    assert provider.invocation_count == 1
    assert verify_opaque_provider_receipt(
        receipt,
        public_key_bytes=signer.public_key_bytes,
    ) is True

    # A restarted custody process retrieves the durable receipt; it does not invoke
    # the provider again, even though the original authorization window is expired.
    restarted = opaque_service(
        tmp_path,
        OpaqueProviderReleaseSigner(provider),
        human_public,
    )
    again = restarted.execute_release(request, now=now + timedelta(minutes=20))
    assert again == receipt
    assert provider.invocation_count == 1


def test_changed_envelope_cannot_reconcile_committed_provider_operation(tmp_path):
    provider = ReferenceOpaqueMlDsa65Provider(ack_loss_once=True)
    signer = OpaqueProviderReleaseSigner(provider)
    request, _signer, human_public, now = fixture(signer=signer)
    svc = opaque_service(tmp_path, signer, human_public)

    with pytest.raises(CustodyIndeterminate):
        svc.execute_release(request, now=now + timedelta(seconds=1))

    changed = deepcopy(request)
    changed["broadcast_requested"] = True
    with pytest.raises((CustodyConflict, ValueError)):
        svc.reconcile_release(changed)
    assert provider.invocation_count == 1


class AmbiguousWithoutCommitProvider(ReferenceOpaqueMlDsa65Provider):
    """Provider timeout before any durable signing result exists."""

    def begin_sign(self, operation_id: str, message: bytes, context: bytes) -> ProviderResult:
        self.invocation_count += 1
        raise ProviderAmbiguousOutcome(operation_id, "simulated timeout before provider commit")

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


def test_provider_not_found_never_auto_retries_consumed_approval(tmp_path):
    provider = AmbiguousWithoutCommitProvider()
    signer = OpaqueProviderReleaseSigner(provider)
    request, _signer, human_public, now = fixture(signer=signer)
    svc = opaque_service(tmp_path, signer, human_public)

    with pytest.raises(CustodyIndeterminate):
        svc.execute_release(request, now=now + timedelta(seconds=1))
    assert provider.invocation_count == 1

    with pytest.raises(CustodyIndeterminate, match="new human authorization"):
        svc.reconcile_release(request)
    assert provider.invocation_count == 1

    ledger = json.loads((tmp_path / "custody-ledger.json").read_text(encoding="utf-8"))
    entry = ledger["requests"][request["request_id"]]
    assert entry["state"] == "INDETERMINATE"
    assert entry["provider_reconciliation_state"] == "NOT_FOUND_SAFE_TO_RETRY"
    assert "new_human_authorization_required" in entry["indeterminate_reason"]


def test_provider_operation_id_is_bound_into_ledger_and_receipt(tmp_path):
    provider = ReferenceOpaqueMlDsa65Provider()
    signer = OpaqueProviderReleaseSigner(provider)
    request, _signer, human_public, now = fixture(signer=signer)
    svc = opaque_service(tmp_path, signer, human_public)

    receipt = svc.execute_release(request, now=now + timedelta(seconds=1))
    assert provider.invocation_count == 1
    assert receipt["provider_reconciled"] is False
    assert receipt["provider_key_handle"] == provider.key_handle
    assert receipt["provider_operation_id"].startswith("QCRYPTO-PROVIDER-")
    assert verify_opaque_provider_receipt(
        receipt,
        public_key_bytes=signer.public_key_bytes,
    ) is True

    ledger = json.loads((tmp_path / "custody-ledger.json").read_text(encoding="utf-8"))
    entry = ledger["requests"][request["request_id"]]
    assert entry["state"] == "SIGNED"
    assert entry["provider_operation_id"] == receipt["provider_operation_id"]
    assert entry["provider_key_handle"] == provider.key_handle
    assert entry["provider_reconciled"] is False
    serialized = json.dumps(ledger).lower()
    assert "private_key_pem" not in serialized
    assert "private_key_bytes" not in serialized
    assert "seed phrase" not in serialized
    assert "mnemonic" not in serialized
