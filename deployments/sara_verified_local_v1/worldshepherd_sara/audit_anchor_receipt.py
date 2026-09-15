from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .audit_checkpoint_anchor import (
    AUDIT_EXTERNAL_ANCHOR_SCHEMA,
    SaraAuditExternalAnchorError,
    load_external_anchor,
)


AUDIT_ANCHOR_PUBLICATION_SCHEMA = "WS-SARA-AUDIT-ANCHOR-PUBLICATION-V1"
AUDIT_ANCHOR_RECEIPT_SCHEMA = "WS-SARA-AUDIT-ANCHOR-RECEIPT-V1"
AUDIT_ANCHOR_RECEIPT_VERIFICATION_SCHEMA = (
    "WS-SARA-AUDIT-ANCHOR-RECEIPT-VERIFICATION-V1"
)
RECEIPT_AUTH_NONE = "NONE"
RECEIPT_AUTH_ED25519 = "ED25519"
RETENTION_NOT_ESTABLISHED = "NOT_ESTABLISHED"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class AuditAnchorReceiptError(ValueError):
    pass


class AuditAnchorSink(Protocol):
    """Provider-neutral publication boundary for externally retaining an anchor.

    Implementations may copy an anchor to another system and return a receipt.
    This protocol does not imply that the destination is immutable, WORM,
    independently operated, or otherwise suitable for a compliance claim.
    """

    def publish(self, publication: dict[str, Any]) -> dict[str, Any]: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _decode_public_key(value: str) -> bytes:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.b64decode(
            padded.encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, UnicodeEncodeError) as exc:
        raise AuditAnchorReceiptError("receipt provider public key is invalid") from exc
    if len(raw) != 32:
        raise AuditAnchorReceiptError(
            "receipt provider Ed25519 public key must be 32 bytes"
        )
    return raw


def build_anchor_publication(anchor_path: str) -> dict[str, Any]:
    try:
        anchor = load_external_anchor(anchor_path)
    except SaraAuditExternalAnchorError as exc:
        raise AuditAnchorReceiptError(str(exc)) from exc
    if anchor.get("schema") != AUDIT_EXTERNAL_ANCHOR_SCHEMA:
        raise AuditAnchorReceiptError("external anchor schema mismatch")
    return {
        "schema": AUDIT_ANCHOR_PUBLICATION_SCHEMA,
        "anchor_sha256": anchor["anchor_sha256"],
        "checkpoint_sha256": anchor["checkpoint_sha256"],
        "checkpoint_sequence": anchor["checkpoint_sequence"],
        "checkpoint_record_count": anchor["checkpoint_record_count"],
        "checkpoint_created_at": anchor["checkpoint_created_at"],
        "signing_key_id": anchor["key_id"],
        "signing_key_fingerprint_sha256": anchor["key_fingerprint_sha256"],
        "claims_boundary": (
            "Publication requests portability of the external checkpoint pin only. "
            "It does not establish provider acceptance, immutability, WORM retention, "
            "third-party attestation, or compliance status."
        ),
    }


def _validate_publication(publication: Any) -> dict[str, Any]:
    if not isinstance(publication, dict) or publication.get("schema") != AUDIT_ANCHOR_PUBLICATION_SCHEMA:
        raise AuditAnchorReceiptError("anchor publication schema mismatch")
    for field in (
        "anchor_sha256",
        "checkpoint_sha256",
        "signing_key_fingerprint_sha256",
    ):
        value = publication.get(field)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise AuditAnchorReceiptError(f"anchor publication {field} is invalid")
    sequence = publication.get("checkpoint_sequence")
    record_count = publication.get("checkpoint_record_count")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise AuditAnchorReceiptError("anchor publication sequence is invalid")
    if not isinstance(record_count, int) or isinstance(record_count, bool) or record_count < 1:
        raise AuditAnchorReceiptError("anchor publication record count is invalid")
    key_id = publication.get("signing_key_id")
    if not isinstance(key_id, str) or not _SAFE_ID.fullmatch(key_id):
        raise AuditAnchorReceiptError("anchor publication signing key ID is invalid")
    created_at = publication.get("checkpoint_created_at")
    if not isinstance(created_at, str) or not created_at:
        raise AuditAnchorReceiptError("anchor publication checkpoint timestamp is invalid")
    return publication


def receipt_signing_payload(receipt: dict[str, Any]) -> bytes:
    unsigned = dict(receipt)
    unsigned.pop("signature_b64url", None)
    return _canonical(unsigned)


def verify_anchor_receipt(
    *,
    publication: dict[str, Any],
    receipt: dict[str, Any],
    trusted_provider_fingerprint_sha256: str | None = None,
) -> dict[str, Any]:
    publication = _validate_publication(publication)
    if not isinstance(receipt, dict) or receipt.get("schema") != AUDIT_ANCHOR_RECEIPT_SCHEMA:
        raise AuditAnchorReceiptError("anchor receipt schema mismatch")

    sink_id = receipt.get("sink_id")
    receipt_id = receipt.get("receipt_id")
    accepted_at = receipt.get("accepted_at")
    if not isinstance(sink_id, str) or not _SAFE_ID.fullmatch(sink_id):
        raise AuditAnchorReceiptError("anchor receipt sink ID is invalid")
    if not isinstance(receipt_id, str) or not _SAFE_ID.fullmatch(receipt_id):
        raise AuditAnchorReceiptError("anchor receipt ID is invalid")
    if not isinstance(accepted_at, str) or not accepted_at:
        raise AuditAnchorReceiptError("anchor receipt acceptance timestamp is invalid")

    for field in (
        "anchor_sha256",
        "checkpoint_sha256",
        "checkpoint_sequence",
        "checkpoint_record_count",
    ):
        if receipt.get(field) != publication.get(field):
            raise AuditAnchorReceiptError(
                f"anchor receipt {field} does not match publication"
            )

    if receipt.get("retention_status") != RETENTION_NOT_ESTABLISHED:
        raise AuditAnchorReceiptError(
            "generic anchor receipt must not assert an unverified retention guarantee"
        )

    authentication = receipt.get("provider_authentication")
    provider_fingerprint: str | None = None
    if authentication == RECEIPT_AUTH_NONE:
        if trusted_provider_fingerprint_sha256 is not None:
            raise AuditAnchorReceiptError(
                "trusted provider fingerprint supplied for unauthenticated receipt"
            )
        if receipt.get("signature_b64url") is not None or receipt.get("provider_public_key_b64url") is not None:
            raise AuditAnchorReceiptError(
                "unauthenticated receipt contains unexpected signature material"
            )
        verification_state = "ACKNOWLEDGED_UNAUTHENTICATED"
    elif authentication == RECEIPT_AUTH_ED25519:
        encoded_public = receipt.get("provider_public_key_b64url")
        encoded_signature = receipt.get("signature_b64url")
        provider_fingerprint = receipt.get("provider_key_fingerprint_sha256")
        if not isinstance(encoded_public, str) or not encoded_public:
            raise AuditAnchorReceiptError("authenticated receipt public key is missing")
        if not isinstance(encoded_signature, str) or not encoded_signature:
            raise AuditAnchorReceiptError("authenticated receipt signature is missing")
        if not isinstance(provider_fingerprint, str) or not _SHA256.fullmatch(provider_fingerprint):
            raise AuditAnchorReceiptError(
                "authenticated receipt provider fingerprint is invalid"
            )
        public_bytes = _decode_public_key(encoded_public)
        actual_fingerprint = hashlib.sha256(public_bytes).hexdigest()
        if actual_fingerprint != provider_fingerprint:
            raise AuditAnchorReceiptError(
                "authenticated receipt public key fingerprint mismatch"
            )
        if (
            trusted_provider_fingerprint_sha256 is not None
            and provider_fingerprint != trusted_provider_fingerprint_sha256
        ):
            raise AuditAnchorReceiptError(
                "authenticated receipt provider is not the trusted provider"
            )
        try:
            padded = encoded_signature + "=" * (-len(encoded_signature) % 4)
            signature = base64.b64decode(
                padded.encode("ascii"),
                altchars=b"-_",
                validate=True,
            )
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                signature,
                receipt_signing_payload(receipt),
            )
        except (ValueError, UnicodeEncodeError, InvalidSignature) as exc:
            raise AuditAnchorReceiptError(
                "authenticated anchor receipt signature verification failed"
            ) from exc
        verification_state = "AUTHENTICATED_RECEIPT"
    else:
        raise AuditAnchorReceiptError("anchor receipt authentication mode is invalid")

    return {
        "schema": AUDIT_ANCHOR_RECEIPT_VERIFICATION_SCHEMA,
        "status": "PASS",
        "verification_state": verification_state,
        "sink_id": sink_id,
        "receipt_id": receipt_id,
        "anchor_sha256": publication["anchor_sha256"],
        "checkpoint_sha256": publication["checkpoint_sha256"],
        "provider_key_fingerprint_sha256": provider_fingerprint,
        "retention_status": RETENTION_NOT_ESTABLISHED,
        "claims_boundary": (
            "PASS establishes receipt/publication consistency and, when configured, "
            "receipt-signature authenticity for the supplied provider key. It does not "
            "establish immutable or WORM retention, provider independence, public transparency, "
            "third-party attestation, or regulatory compliance."
        ),
    }
