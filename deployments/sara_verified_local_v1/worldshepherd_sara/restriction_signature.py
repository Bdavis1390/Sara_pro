from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .event_outbox import queue_event_outbox_patch
from .limits import validate_json_resource
from .prime_sentinel_authorization import (
    PrimeSentinelVerifier,
)
from .restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RestrictionEvidence,
)


RESTRICTION_SIGNATURE_SCHEMA = "WS-RESTRICTION-PRIME-SIGNATURE-V1"
SIGNED_RESTRICTION_SCHEMA = "WS-RESTRICTION-PROVENANCE-V4"
RESTRICTION_SIGNATURE_DOMAIN = b"WS-RESTRICTION-PRIME-SIGNATURE-V1\x00"


def canonical_restriction_signature_message(
    evidence: RestrictionEvidence,
    *,
    signing_key_id: str,
) -> bytes:
    """Build the exact domain-separated message an external PRIME signer signs."""
    if not isinstance(signing_key_id, str) or not signing_key_id:
        raise ValueError("signing_key_id must be non-empty")
    payload = {
        "schema": RESTRICTION_SIGNATURE_SCHEMA,
        "issuer": RESTRICTION_AUTHORITY,
        "signing_key_id": signing_key_id,
        "restriction": evidence.semantic_document(),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return RESTRICTION_SIGNATURE_DOMAIN + canonical


@dataclass(frozen=True)
class VerifiedRestrictionSignature:
    schema: str
    restriction_id: str
    signing_key_id: str
    signing_key_fingerprint_sha256: str
    signature_b64url: str
    signed_message_sha256: str

    def semantic_document(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "restriction_id": self.restriction_id,
            "signing_key_id": self.signing_key_id,
            "signing_key_fingerprint_sha256": self.signing_key_fingerprint_sha256,
            "signature_b64url": self.signature_b64url,
            "signed_message_sha256": self.signed_message_sha256,
        }


def verify_restriction_signature(
    evidence: RestrictionEvidence,
    *,
    signing_key_id: str,
    signature_b64url: str,
    verifier: PrimeSentinelVerifier,
) -> VerifiedRestrictionSignature:
    """Verify externally signed safe restriction evidence with PRIME public keys only."""
    message = canonical_restriction_signature_message(
        evidence,
        signing_key_id=signing_key_id,
    )
    verified = verifier.verify_detached_signature(
        key_id=signing_key_id,
        message=message,
        signature_b64url=signature_b64url,
    )
    return VerifiedRestrictionSignature(
        schema=RESTRICTION_SIGNATURE_SCHEMA,
        restriction_id=evidence.restriction_id,
        signing_key_id=verified.key_id,
        signing_key_fingerprint_sha256=verified.key_fingerprint_sha256,
        signature_b64url=signature_b64url,
        signed_message_sha256=hashlib.sha256(message).hexdigest(),
    )


@dataclass(frozen=True)
class VerifiedSignedRestriction:
    restriction: RestrictionEvidence
    signature: VerifiedRestrictionSignature

    @property
    def restriction_id(self) -> str:
        return self.restriction.restriction_id

    @property
    def outbox_event_id(self) -> str:
        return self.restriction.outbox_event_id

    def semantic_document(self) -> dict[str, object]:
        return {
            "schema": SIGNED_RESTRICTION_SCHEMA,
            "restriction": self.restriction.semantic_document(),
            "prime_signature": self.signature.semantic_document(),
            "raw_content_persisted": False,
        }


def bind_verified_restriction_signature(
    evidence: RestrictionEvidence,
    *,
    signing_key_id: str,
    signature_b64url: str,
    verifier: PrimeSentinelVerifier,
) -> VerifiedSignedRestriction:
    verified = verify_restriction_signature(
        evidence,
        signing_key_id=signing_key_id,
        signature_b64url=signature_b64url,
        verifier=verifier,
    )
    return VerifiedSignedRestriction(
        restriction=evidence,
        signature=verified,
    )


def queue_signed_restriction_event(
    registry: dict[str, object],
    signed: VerifiedSignedRestriction,
) -> tuple[dict[str, object], str]:
    """Queue only a signature-verified V4 restriction envelope."""
    payload = signed.semantic_document()
    validate_json_resource(payload)
    return queue_event_outbox_patch(
        registry,
        event=RESTRICTION_EVENT,
        actor=RESTRICTION_AUTHORITY,
        payload=payload,
        event_id=signed.outbox_event_id,
    )
