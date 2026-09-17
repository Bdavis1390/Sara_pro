from __future__ import annotations

import base64
import json
from collections.abc import Callable, Iterable
from typing import Literal

from pydantic import BaseModel, Field


PROVENANCE_ATTESTATION_SCHEMA = "WS-PROVENANCE-ATTESTATION-V1"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ProvenanceAttestation(BaseModel):
    schema: Literal[PROVENANCE_ATTESTATION_SCHEMA] = PROVENANCE_ATTESTATION_SCHEMA
    package_digest: str = Field(pattern=_SHA256_PATTERN)
    signer_id: str = Field(min_length=1, max_length=128)
    key_id: str = Field(min_length=1, max_length=256)
    algorithm: str = Field(min_length=1, max_length=64)
    issued_utc: str = Field(min_length=1, max_length=64)
    signature_b64: str = Field(min_length=1)


Signer = Callable[[bytes], bytes]
Verifier = Callable[[bytes, bytes, str, str], bool]


def _canonical_message(
    *,
    package_digest: str,
    signer_id: str,
    key_id: str,
    algorithm: str,
    issued_utc: str,
) -> bytes:
    payload = {
        "schema": PROVENANCE_ATTESTATION_SCHEMA,
        "package_digest": package_digest,
        "signer_id": signer_id,
        "key_id": key_id,
        "algorithm": algorithm,
        "issued_utc": issued_utc,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def create_provenance_attestation(
    *,
    package_digest: str,
    signer_id: str,
    key_id: str,
    algorithm: str,
    issued_utc: str,
    signer: Signer,
) -> ProvenanceAttestation:
    message = _canonical_message(
        package_digest=package_digest,
        signer_id=signer_id,
        key_id=key_id,
        algorithm=algorithm,
        issued_utc=issued_utc,
    )
    signature = signer(message)
    if not isinstance(signature, bytes) or not signature:
        raise ValueError("signer must return non-empty signature bytes")
    return ProvenanceAttestation(
        package_digest=package_digest,
        signer_id=signer_id,
        key_id=key_id,
        algorithm=algorithm,
        issued_utc=issued_utc,
        signature_b64=base64.b64encode(signature).decode("ascii"),
    )


def verify_provenance_attestation(
    attestation: ProvenanceAttestation,
    *,
    verifier: Verifier,
    trusted_signer_ids: Iterable[str] | None = None,
    trusted_key_ids: Iterable[str] | None = None,
    trusted_algorithms: Iterable[str] | None = None,
) -> bool:
    if trusted_signer_ids is not None and attestation.signer_id not in set(trusted_signer_ids):
        return False
    if trusted_key_ids is not None and attestation.key_id not in set(trusted_key_ids):
        return False
    if trusted_algorithms is not None and attestation.algorithm not in set(trusted_algorithms):
        return False

    try:
        signature = base64.b64decode(attestation.signature_b64, validate=True)
    except (ValueError, TypeError):
        return False
    if not signature:
        return False

    message = _canonical_message(
        package_digest=attestation.package_digest,
        signer_id=attestation.signer_id,
        key_id=attestation.key_id,
        algorithm=attestation.algorithm,
        issued_utc=attestation.issued_utc,
    )
    try:
        return bool(
            verifier(
                message,
                signature,
                attestation.algorithm,
                attestation.key_id,
            )
        )
    except Exception:
        return False
