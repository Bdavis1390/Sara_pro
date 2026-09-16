"""Opaque-provider custody execution with restart-safe reconciliation.

This layer extends the isolated custody domain without expanding SARA authority.
It persists the exact release binding and deterministic provider operation ID before
calling an opaque signer provider.  If the provider acknowledgement is lost, a
later reconciliation may recover the already-committed signature without invoking
``begin_sign`` again.

Important boundary: reconciliation never authorizes a new signature.  A provider
response of NOT_FOUND_SAFE_TO_RETRY is *not* automatically retried; human review is
required instead.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .custody import (
    CustodyConflict,
    CustodyError,
    CustodyIndeterminate,
    _b64decode,
    _canonical,
    _release_binding,
    _sha,
    _utc,
    _utc_text,
    _validate_request,
)
from .durable_service import (
    DurableExternalCustodyService,
    _canonical_envelope_digest,
)
from .opaque_provider import (
    OpaqueProviderReleaseSigner,
    ProviderAmbiguousOutcome,
    ProviderResult,
    ProviderState,
    provider_operation_id,
    verify_provider_result,
)
from .strict_service import _EXPECTED_TOP_LEVEL, _reject_secret_shaped_fields


_PROVIDER_CLAIMS_BOUNDARY = (
    "Opaque-provider custody release attestation only. The private key remains behind "
    "an opaque provider handle. This is not a Bitcoin/Ethereum native transaction "
    "signature, does not broadcast a transaction, does not move value, does not enable "
    "mainnet, and does not establish production HSM integration, FIPS validation, or "
    "end-to-end post-quantum chain security."
)


def _strict_surface(request: dict[str, Any]) -> None:
    if not isinstance(request, dict):
        raise CustodyError("custody request must be a JSON object")
    actual = frozenset(request)
    if actual != _EXPECTED_TOP_LEVEL:
        missing = sorted(_EXPECTED_TOP_LEVEL - actual)
        extra = sorted(actual - _EXPECTED_TOP_LEVEL)
        detail: list[str] = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if extra:
            detail.append("extra=" + ",".join(extra))
        raise CustodyError("custody request surface mismatch: " + "; ".join(detail))
    _reject_secret_shaped_fields(request)


def _provider_receipt(
    *,
    binding: dict[str, Any],
    result: ProviderResult,
    signer: OpaqueProviderReleaseSigner,
    reconciled: bool,
) -> dict[str, Any]:
    if result.state is not ProviderState.SIGNED or not result.signature_b64url:
        raise CustodyError("provider result is not a signed custody release")
    payload = _canonical(binding)
    expected_operation = provider_operation_id(
        key_handle=signer.provider.key_handle,
        message=payload,
        context=signer.context,
    )
    if result.operation_id != expected_operation:
        raise CustodyError("provider operation ID does not match the signed release binding")
    if result.key_handle != signer.provider.key_handle:
        raise CustodyError("provider key handle changed during custody release")
    if not verify_provider_result(
        result,
        public_key_bytes=signer.public_key_bytes,
        message=payload,
        context=signer.context,
    ):
        raise CustodyError("provider signature failed independent custody verification")

    receipt = {
        **binding,
        "state": "SIGNED_CUSTODY_RELEASE_ATTESTATION",
        "signature_b64url": result.signature_b64url,
        "provider_operation_id": result.operation_id,
        "provider_key_handle": result.key_handle,
        "provider_reconciled": reconciled,
        "claims_boundary": _PROVIDER_CLAIMS_BOUNDARY,
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


def verify_opaque_provider_receipt(
    receipt: dict[str, Any],
    *,
    public_key_bytes: bytes,
) -> bool:
    """Verify receipt integrity, provider operation binding, and ML-DSA signature."""
    try:
        receipt_digest = receipt.get("receipt_sha256")
        unsigned_receipt = dict(receipt)
        unsigned_receipt.pop("receipt_sha256", None)
        if receipt_digest != _sha(unsigned_receipt):
            return False

        operation_id = receipt.get("provider_operation_id")
        key_handle = receipt.get("provider_key_handle")
        signature_b64url = receipt.get("signature_b64url")
        if not isinstance(operation_id, str) or not isinstance(key_handle, str):
            return False
        if not isinstance(signature_b64url, str):
            return False

        binding = {
            key: value
            for key, value in receipt.items()
            if key
            not in {
                "state",
                "signature_b64url",
                "provider_operation_id",
                "provider_key_handle",
                "provider_reconciled",
                "claims_boundary",
                "receipt_sha256",
            }
        }
        payload = _canonical(binding)
        context_text = binding.get("signature_context")
        if not isinstance(context_text, str):
            return False
        context = context_text.encode("ascii")
        expected_operation = provider_operation_id(
            key_handle=key_handle,
            message=payload,
            context=context,
        )
        if operation_id != expected_operation:
            return False
        result = ProviderResult(
            operation_id=operation_id,
            state=ProviderState.SIGNED,
            key_handle=key_handle,
            algorithm=str(binding.get("signing_algorithm")),
            message_sha256=__import__("hashlib").sha256(payload).hexdigest(),
            context_sha256=__import__("hashlib").sha256(context).hexdigest(),
            signature_b64url=signature_b64url,
            safe_to_retry=False,
        )
        return verify_provider_result(
            result,
            public_key_bytes=public_key_bytes,
            message=payload,
            context=context,
        )
    except (CustodyError, UnicodeEncodeError, ValueError, TypeError):
        return False


class OpaqueProviderCustodyService(DurableExternalCustodyService):
    """Durable custody service for an opaque signer/HSM-style provider.

    ``execute_release`` crosses the provider invocation fence at most once for a
    request.  ``reconcile_release`` can only recover a previously committed provider
    result; it never calls ``begin_sign`` and therefore cannot create a second
    signature operation.
    """

    signer: OpaqueProviderReleaseSigner

    def __init__(self, *, signer: OpaqueProviderReleaseSigner, **kwargs: Any) -> None:
        super().__init__(signer=signer, **kwargs)
        self.signer = signer

    def execute_release(
        self,
        request: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        _strict_surface(request)
        request_id, envelope_digest = _canonical_envelope_digest(request)
        fast = self._reserve_or_retrieve(request_id, envelope_digest)
        if fast is not None:
            if not verify_opaque_provider_receipt(
                fast,
                public_key_bytes=self.signer.public_key_bytes,
            ):
                raise CustodyError("persisted opaque-provider receipt failed verification")
            return fast

        current = _utc(now or datetime.now(timezone.utc))
        try:
            request_id, approval, semantic, unsigned_payload, handoff_digest = _validate_request(
                request,
                policy=self.policy,
                signer=self.signer,
                trusted_human_keys=self.trusted_human_keys,
                now=current,
            )
            request_digest = _sha(semantic)
            approval_id = approval["approval_id"]
            signed_at = datetime.now(timezone.utc)
            binding = _release_binding(
                request_digest=request_digest,
                handoff_digest=handoff_digest,
                intent_digest=approval["intent_sha256"],
                unsigned_payload_sha256=__import__("hashlib").sha256(unsigned_payload).hexdigest(),
                approval_id=approval_id,
                signer=self.signer,
                network_identity_sha256=approval["network_identity_sha256"],
                destination_commitment_sha256=semantic["intent"]["destination_commitment_sha256"],
                signed_at=signed_at,
            )
            payload = _canonical(binding)
            operation_id = provider_operation_id(
                key_handle=self.signer.provider.key_handle,
                message=payload,
                context=self.signer.context,
            )

            with self.ledger.locked() as locked:
                assert locked.value is not None
                requests = locked.value["requests"]
                used = locked.value["used_approvals"]
                prior = requests.get(request_id)
                if isinstance(prior, dict):
                    raise CustodyConflict("request entered custody state during provider preparation")
                used_by = used.get(approval_id)
                if used_by is not None and used_by != request_id:
                    raise CustodyConflict(
                        "human approval_id has already been consumed by another custody request"
                    )
                requests[request_id] = {
                    "state": "INVOKING",
                    "request_sha256": request_digest,
                    "approval_id": approval_id,
                    "handoff_package_sha256": handoff_digest,
                    "intent_sha256": approval["intent_sha256"],
                    "invoking_at": _utc_text(current),
                    "release_binding": deepcopy(binding),
                    "provider_operation_id": operation_id,
                    "provider_key_handle": self.signer.provider.key_handle,
                    "provider_signer_fingerprint_sha256": self.signer.fingerprint_sha256,
                    "provider_message_sha256": __import__("hashlib").sha256(payload).hexdigest(),
                    "provider_context_sha256": __import__("hashlib").sha256(self.signer.context).hexdigest(),
                }
                used[approval_id] = request_id
                locked.commit()

            try:
                result = self.signer.provider.begin_sign(
                    operation_id,
                    payload,
                    self.signer.context,
                )
            except ProviderAmbiguousOutcome as exc:
                self._mark_indeterminate(
                    request_id,
                    request_digest,
                    operation_id,
                    "provider_acknowledgement_lost_or_outcome_ambiguous",
                )
                raise CustodyIndeterminate(
                    "provider outcome is indeterminate; reconcile by operation ID before any new authorization"
                ) from exc
            except Exception as exc:
                self._mark_indeterminate(
                    request_id,
                    request_digest,
                    operation_id,
                    "provider_invocation_failed_without_confirmed_receipt",
                )
                raise CustodyIndeterminate(
                    "provider invocation outcome is indeterminate; automatic retry is forbidden"
                ) from exc

            receipt = _provider_receipt(
                binding=binding,
                result=result,
                signer=self.signer,
                reconciled=False,
            )
            self._commit_signed(
                request_id=request_id,
                request_digest=request_digest,
                operation_id=operation_id,
                receipt=receipt,
                reconciled=False,
            )
            return receipt
        except Exception:
            self._cleanup_failed_reservation(request_id, envelope_digest)
            raise

    def _mark_indeterminate(
        self,
        request_id: str,
        request_digest: str,
        operation_id: str,
        reason: str,
    ) -> None:
        with self.ledger.locked() as locked:
            assert locked.value is not None
            entry = locked.value["requests"].get(request_id)
            if (
                isinstance(entry, dict)
                and entry.get("state") == "INVOKING"
                and entry.get("request_sha256") == request_digest
                and entry.get("provider_operation_id") == operation_id
            ):
                entry["state"] = "INDETERMINATE"
                entry["indeterminate_reason"] = reason
                locked.commit()

    def _commit_signed(
        self,
        *,
        request_id: str,
        request_digest: str,
        operation_id: str,
        receipt: dict[str, Any],
        reconciled: bool,
    ) -> None:
        with self.ledger.locked() as locked:
            assert locked.value is not None
            entry = locked.value["requests"].get(request_id)
            if not isinstance(entry, dict):
                raise CustodyIndeterminate("custody request disappeared after provider invocation")
            if entry.get("state") not in {"INVOKING", "INDETERMINATE"}:
                raise CustodyIndeterminate("custody state changed during provider completion")
            if entry.get("request_sha256") != request_digest:
                raise CustodyIndeterminate("custody request digest changed during provider completion")
            if entry.get("provider_operation_id") != operation_id:
                raise CustodyIndeterminate("provider operation ID changed during provider completion")
            entry["state"] = "SIGNED"
            entry["signed_at"] = receipt["signed_at"]
            entry["provider_reconciled"] = reconciled
            entry["receipt"] = receipt
            locked.commit()

    def reconcile_release(self, request: dict[str, Any]) -> dict[str, Any]:
        """Resolve one ambiguous provider operation without invoking sign again.

        This method deliberately does not re-check approval freshness.  The original
        request crossed the invocation fence only after full validation and the exact
        request envelope was durably committed.  Reconciliation is recovery of that
        historical operation, not authorization for a new one.
        """
        _strict_surface(request)
        request_id, envelope_digest = _canonical_envelope_digest(request)

        with self.ledger.locked() as locked:
            assert locked.value is not None
            envelopes = locked.value.get("request_envelopes")
            if not isinstance(envelopes, dict) or envelopes.get(request_id) != envelope_digest:
                raise CustodyConflict("reconciliation request does not match the exact committed envelope")
            entry = locked.value["requests"].get(request_id)
            if not isinstance(entry, dict):
                raise CustodyConflict("custody request has no durable invocation record")
            if entry.get("state") == "SIGNED":
                receipt = entry.get("receipt")
                if not isinstance(receipt, dict) or not verify_opaque_provider_receipt(
                    receipt,
                    public_key_bytes=self.signer.public_key_bytes,
                ):
                    raise CustodyError("persisted opaque-provider receipt failed verification")
                return dict(receipt)
            if entry.get("state") not in {"INVOKING", "INDETERMINATE"}:
                raise CustodyConflict("custody request is not reconcilable")
            binding = deepcopy(entry.get("release_binding"))
            if not isinstance(binding, dict):
                raise CustodyError("custody invocation record is missing the release binding")
            operation_id = entry.get("provider_operation_id")
            request_digest = entry.get("request_sha256")
            if not isinstance(operation_id, str) or not isinstance(request_digest, str):
                raise CustodyError("custody invocation record is missing provider identity")
            if entry.get("provider_key_handle") != self.signer.provider.key_handle:
                raise CustodyConflict("current provider key handle differs from the invoked custody operation")
            if entry.get("provider_signer_fingerprint_sha256") != self.signer.fingerprint_sha256:
                raise CustodyConflict("current provider signer differs from the invoked custody operation")

        payload = _canonical(binding)
        expected_operation = provider_operation_id(
            key_handle=self.signer.provider.key_handle,
            message=payload,
            context=self.signer.context,
        )
        if expected_operation != operation_id:
            raise CustodyError("stored provider operation ID does not reconstruct from custody evidence")

        result = self.signer.provider.reconcile(operation_id)
        if result.operation_id != operation_id:
            raise CustodyError("provider reconciliation returned the wrong operation ID")
        if result.state is ProviderState.SIGNED:
            receipt = _provider_receipt(
                binding=binding,
                result=result,
                signer=self.signer,
                reconciled=True,
            )
            self._commit_signed(
                request_id=request_id,
                request_digest=request_digest,
                operation_id=operation_id,
                receipt=receipt,
                reconciled=True,
            )
            return receipt

        with self.ledger.locked() as locked:
            assert locked.value is not None
            entry = locked.value["requests"].get(request_id)
            if isinstance(entry, dict) and entry.get("provider_operation_id") == operation_id:
                entry["state"] = "INDETERMINATE"
                entry["provider_reconciliation_state"] = result.state.value
                if result.state is ProviderState.NOT_FOUND_SAFE_TO_RETRY:
                    entry["indeterminate_reason"] = (
                        "provider_reports_operation_not_found_new_human_authorization_required"
                    )
                else:
                    entry["indeterminate_reason"] = "provider_operation_not_yet_confirmed"
                locked.commit()

        if result.state is ProviderState.NOT_FOUND_SAFE_TO_RETRY:
            raise CustodyIndeterminate(
                "provider reports no committed signature; automatic retry remains forbidden and new human authorization is required"
            )
        raise CustodyIndeterminate(
            "provider operation remains unresolved; automatic retry is forbidden"
        )
