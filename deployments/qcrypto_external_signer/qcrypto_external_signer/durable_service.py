"""Expiry-safe public custody service with exact-envelope retry identity.

A confirmed custody release is a durable fact. Exact retrieval of that fact must not
require a still-live human approval, because retrying a receipt is not a new signing
authorization. This layer records only a SHA-256 of the exact request envelope before
delegating to the strict custody engine.

Changed request content still conflicts. INVOKING or INDETERMINATE requests still
fail closed. No signer call is made by the fast-path receipt retrieval.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from .custody import (
    REQUEST_SCHEMA,
    CustodyConflict,
    CustodyError,
    CustodyIndeterminate,
    verify_release_receipt,
)
from .strict_service import StrictExternalCustodyService

_ENVELOPE_MAP_KEY = "request_envelopes"


def _canonical_envelope_digest(request: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(request, dict):
        raise CustodyError("custody request must be a JSON object")
    if request.get("schema") != REQUEST_SCHEMA:
        raise CustodyError("unsupported external custody request schema")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
        raise CustodyError("request_id is invalid")
    try:
        encoded = json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CustodyError("custody request is not canonical JSON") from exc
    return request_id, hashlib.sha256(encoded).hexdigest()


class DurableExternalCustodyService(StrictExternalCustodyService):
    """Supported custody entry point with durable exact-retry receipt semantics."""

    def _verify_durable_receipt(self, receipt: dict[str, Any]) -> bool:
        """Dispatch to the receipt verifier for the concrete custody signer class.

        Provider-augmented receipts have additional operation-binding fields that are
        intentionally outside the signed release binding.  They must therefore use the
        opaque-provider verifier, which authenticates the signed binding *and*
        reconstructs the provider operation ID.  Falling back to the generic verifier
        here would either reject a valid provider receipt after restart or tempt callers
        to weaken the provider metadata binding.
        """
        if "provider_operation_id" in receipt:
            # Local import avoids a module-import cycle: provider_custody subclasses
            # this service, while this path executes only after all modules are loaded.
            from .provider_custody import verify_opaque_provider_receipt

            return verify_opaque_provider_receipt(
                receipt,
                public_key_bytes=self.signer.public_key_bytes,
            )
        return verify_release_receipt(receipt, self.signer.public_key_bytes)

    def _reserve_or_retrieve(
        self,
        request_id: str,
        envelope_digest: str,
    ) -> dict[str, Any] | None:
        with self.ledger.locked() as locked:
            assert locked.value is not None
            envelopes = locked.value.setdefault(_ENVELOPE_MAP_KEY, {})
            if not isinstance(envelopes, dict):
                raise CustodyError("custody request-envelope ledger is invalid")
            prior_envelope = envelopes.get(request_id)
            if prior_envelope is not None and prior_envelope != envelope_digest:
                raise CustodyConflict("request_id was reused with changed exact envelope content")
            if prior_envelope is None:
                envelopes[request_id] = envelope_digest
                locked.commit()

            prior = locked.value["requests"].get(request_id)
            if not isinstance(prior, dict):
                return None
            state = prior.get("state")
            if state == "SIGNED":
                receipt = prior.get("receipt")
                if not isinstance(receipt, dict):
                    raise CustodyError("signed custody entry is missing its receipt")
                if not self._verify_durable_receipt(receipt):
                    raise CustodyError("persisted custody receipt failed integrity verification")
                return dict(receipt)
            if state == "INVOKING":
                prior["state"] = "INDETERMINATE"
                prior["indeterminate_reason"] = (
                    "restart_or_retry_observed_after_invocation_fence"
                )
                locked.commit()
                raise CustodyIndeterminate(
                    "signer outcome is indeterminate; automatic retry is forbidden"
                )
            if state == "INDETERMINATE":
                raise CustodyIndeterminate(
                    "signer outcome is indeterminate; human reconciliation is required"
                )
            raise CustodyConflict("request is in an unsupported custody state")

    def _cleanup_failed_reservation(
        self,
        request_id: str,
        envelope_digest: str,
    ) -> None:
        with self.ledger.locked() as locked:
            assert locked.value is not None
            envelopes = locked.value.get(_ENVELOPE_MAP_KEY)
            requests = locked.value.get("requests")
            if not isinstance(envelopes, dict) or not isinstance(requests, dict):
                return
            # Preserve the envelope identity once the core service crossed its
            # durable invocation fence. If validation failed before that point,
            # release the reservation so a corrected request ID is not squatted.
            if request_id not in requests and envelopes.get(request_id) == envelope_digest:
                del envelopes[request_id]
                locked.commit()

    def execute_release(
        self,
        request: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        request_id, envelope_digest = _canonical_envelope_digest(request)
        fast = self._reserve_or_retrieve(request_id, envelope_digest)
        if fast is not None:
            return fast
        try:
            receipt = super().execute_release(request, now=now)
        except Exception:
            self._cleanup_failed_reservation(request_id, envelope_digest)
            raise
        # Core persistence is already authoritative. The envelope map remains as
        # the immutable exact-request identity used by later receipt retrieval.
        return receipt
