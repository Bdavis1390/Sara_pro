from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .audit_checkpoint import (
    AUDIT_CHECKPOINT_BUNDLE_SCHEMA,
    AUDIT_CHECKPOINT_PUBLIC_KEY_SCHEMA,
    AUDIT_CHECKPOINT_SCHEMA,
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SaraAuditCheckpointVerificationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise SaraAuditCheckpointVerificationError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _b64url_decode(value: Any, *, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise SaraAuditCheckpointVerificationError(
            f"{label} must be non-empty base64url text"
        )
    try:
        padded = value + "=" * (-len(value) % 4)
        return base64.b64decode(
            padded.encode("ascii"), altchars=b"-_", validate=True
        )
    except (ValueError, UnicodeEncodeError) as exc:
        raise SaraAuditCheckpointVerificationError(
            f"{label} is not valid base64url"
        ) from exc


def verify_checkpoint_bundle(
    bundle: Any,
    expected_fingerprint: str,
) -> dict[str, Any]:
    expected_fingerprint = _sha256(
        expected_fingerprint, label="expected public-key fingerprint"
    )
    if not isinstance(bundle, dict) or bundle.get("schema") != AUDIT_CHECKPOINT_BUNDLE_SCHEMA:
        raise SaraAuditCheckpointVerificationError("audit checkpoint bundle schema mismatch")
    manifest = bundle.get("manifest")
    public = bundle.get("public_key")
    if not isinstance(manifest, dict) or manifest.get("schema") != AUDIT_CHECKPOINT_SCHEMA:
        raise SaraAuditCheckpointVerificationError("audit checkpoint manifest schema mismatch")
    if not isinstance(public, dict) or public.get("schema") != AUDIT_CHECKPOINT_PUBLIC_KEY_SCHEMA:
        raise SaraAuditCheckpointVerificationError("audit checkpoint public-key schema mismatch")
    if public.get("issuer") != "SARA":
        raise SaraAuditCheckpointVerificationError("audit checkpoint public-key issuer mismatch")
    if public.get("purpose") != "APPLICATION_AUDIT_CHECKPOINT_SIGNING":
        raise SaraAuditCheckpointVerificationError("audit checkpoint public-key purpose mismatch")
    if manifest.get("issuer") != "SARA" or manifest.get("purpose") != "APPLICATION_AUDIT_PREFIX_INTEGRITY":
        raise SaraAuditCheckpointVerificationError("audit checkpoint manifest purpose mismatch")
    if public.get("algorithm") != "Ed25519" or manifest.get("algorithm") != "Ed25519":
        raise SaraAuditCheckpointVerificationError("audit checkpoint algorithm mismatch")

    public_bytes = _b64url_decode(public.get("public_key_b64url"), label="public key")
    if len(public_bytes) != 32:
        raise SaraAuditCheckpointVerificationError("Ed25519 public key must be 32 bytes")
    actual_fingerprint = hashlib.sha256(public_bytes).hexdigest()
    public_fingerprint = _sha256(
        public.get("fingerprint_sha256"), label="public-key fingerprint"
    )
    manifest_fingerprint = _sha256(
        manifest.get("key_fingerprint_sha256"), label="manifest key fingerprint"
    )
    if not (
        actual_fingerprint
        == public_fingerprint
        == manifest_fingerprint
        == expected_fingerprint
    ):
        raise SaraAuditCheckpointVerificationError(
            "audit checkpoint public-key fingerprint is not trusted"
        )

    key_id = public.get("key_id")
    if not isinstance(key_id, str) or not key_id or manifest.get("key_id") != key_id:
        raise SaraAuditCheckpointVerificationError("audit checkpoint key ID mismatch")
    sequence = manifest.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise SaraAuditCheckpointVerificationError(
            "audit checkpoint sequence must be a positive integer"
        )
    record_count = manifest.get("record_count")
    if not isinstance(record_count, int) or isinstance(record_count, bool) or record_count < 1:
        raise SaraAuditCheckpointVerificationError(
            "audit checkpoint record count must be positive"
        )
    checkpoint_id = manifest.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise SaraAuditCheckpointVerificationError("audit checkpoint ID is missing")
    chain_head = _sha256(
        manifest.get("audit_chain_head_sha256"), label="audit chain head"
    )
    last_record = _sha256(
        manifest.get("last_record_sha256"), label="last record digest"
    )
    previous = manifest.get("previous_checkpoint_sha256")
    if previous is not None:
        previous = _sha256(previous, label="previous checkpoint digest")

    manifest_bytes = _canonical(manifest)
    checkpoint_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if bundle.get("checkpoint_sha256") != checkpoint_digest:
        raise SaraAuditCheckpointVerificationError(
            "audit checkpoint manifest digest mismatch"
        )
    signature = _b64url_decode(
        bundle.get("signature_b64url"), label="audit checkpoint signature"
    )
    if len(signature) != 64:
        raise SaraAuditCheckpointVerificationError(
            "Ed25519 audit checkpoint signature must be 64 bytes"
        )
    try:
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature, manifest_bytes
        )
    except InvalidSignature as exc:
        raise SaraAuditCheckpointVerificationError(
            "audit checkpoint signature verification failed"
        ) from exc

    return {
        "sequence": sequence,
        "checkpoint_id": checkpoint_id,
        "checkpoint_sha256": checkpoint_digest,
        "previous_checkpoint_sha256": previous,
        "record_count": record_count,
        "audit_chain_head_sha256": chain_head,
        "last_record_sha256": last_record,
        "key_id": key_id,
        "key_fingerprint_sha256": expected_fingerprint,
    }


def verify_checkpoint_chain(
    bundles: list[Any],
    expected_fingerprint: str,
    *,
    expected_latest_checkpoint_sha256: str | None = None,
) -> dict[str, Any]:
    if not isinstance(bundles, list) or not bundles:
        raise SaraAuditCheckpointVerificationError(
            "at least one SARA audit checkpoint is required"
        )
    verified: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for bundle in bundles:
        current = verify_checkpoint_bundle(bundle, expected_fingerprint)
        if previous is None:
            if current["sequence"] != 1 or current["previous_checkpoint_sha256"] is not None:
                raise SaraAuditCheckpointVerificationError(
                    "SARA audit checkpoint chain must begin at sequence 1"
                )
        else:
            if current["sequence"] != previous["sequence"] + 1:
                raise SaraAuditCheckpointVerificationError(
                    "SARA audit checkpoint sequence is not contiguous"
                )
            if current["previous_checkpoint_sha256"] != previous["checkpoint_sha256"]:
                raise SaraAuditCheckpointVerificationError(
                    "SARA audit checkpoint predecessor digest mismatch"
                )
            if current["key_id"] != previous["key_id"]:
                raise SaraAuditCheckpointVerificationError(
                    "SARA audit checkpoint key ID changed inside chain"
                )
            if current["record_count"] < previous["record_count"]:
                raise SaraAuditCheckpointVerificationError(
                    "SARA audit checkpoint record count decreased"
                )
            if (
                current["record_count"] == previous["record_count"]
                and current["audit_chain_head_sha256"]
                != previous["audit_chain_head_sha256"]
            ):
                raise SaraAuditCheckpointVerificationError(
                    "same-length SARA audit checkpoint changed chain head"
                )
        verified.append(current)
        previous = current

    assert previous is not None
    if expected_latest_checkpoint_sha256 is not None:
        expected_latest_checkpoint_sha256 = _sha256(
            expected_latest_checkpoint_sha256,
            label="expected latest checkpoint digest",
        )
        if previous["checkpoint_sha256"] != expected_latest_checkpoint_sha256:
            raise SaraAuditCheckpointVerificationError(
                "SARA audit checkpoint ledger rollback/latest-digest mismatch"
            )
    return {
        "schema": "WS-SARA-AUDIT-CHECKPOINT-VERIFICATION-V1",
        "status": "PASS",
        "checkpoint_count": len(verified),
        "first_sequence": verified[0]["sequence"],
        "last_sequence": previous["sequence"],
        "last_checkpoint_sha256": previous["checkpoint_sha256"],
        "last_record_count": previous["record_count"],
        "key_id": previous["key_id"],
        "key_fingerprint_sha256": previous["key_fingerprint_sha256"],
        "external_latest_digest_pin_checked": expected_latest_checkpoint_sha256
        is not None,
        "claims_boundary": (
            "Cryptographic verification of the supplied signed checkpoint chain only; "
            "local privileged rollback resistance requires a separately retained expected "
            "latest checkpoint digest, and signing-key compromise is out of scope."
        ),
    }
