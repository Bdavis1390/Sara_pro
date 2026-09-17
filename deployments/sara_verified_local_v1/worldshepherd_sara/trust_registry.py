from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .provenance_attestation import ProvenanceAttestation, Verifier, verify_provenance_attestation


TRUST_REGISTRY_SCHEMA = "WS-TRUST-REGISTRY-V1"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class TrustKeyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    signer_id: str = Field(min_length=1, max_length=128)
    key_id: str = Field(min_length=1, max_length=256)
    algorithm: str = Field(min_length=1, max_length=64)
    status: Literal["ACTIVE", "RETIRED", "REVOKED"]
    valid_from_utc: str = Field(min_length=1, max_length=64)
    valid_until_utc: str | None = Field(default=None, max_length=64)
    revoked_utc: str | None = Field(default=None, max_length=64)
    successor_key_id: str | None = Field(default=None, max_length=256)


class TrustRegistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema: Literal[TRUST_REGISTRY_SCHEMA] = TRUST_REGISTRY_SCHEMA
    registry_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    generated_utc: str = Field(min_length=1, max_length=64)
    entries: tuple[TrustKeyRecord, ...]
    registry_digest: str = Field(pattern=_SHA256_PATTERN)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone information")
    return parsed.astimezone(timezone.utc)


def _entry_identity(entry: TrustKeyRecord) -> tuple[str, str, str]:
    return (entry.signer_id, entry.key_id, entry.algorithm)


def _validate_entry(entry: TrustKeyRecord) -> None:
    valid_from = _parse_utc(entry.valid_from_utc)
    valid_until = _parse_utc(entry.valid_until_utc) if entry.valid_until_utc else None
    revoked = _parse_utc(entry.revoked_utc) if entry.revoked_utc else None

    if valid_until is not None and valid_until <= valid_from:
        raise ValueError("valid_until_utc must be later than valid_from_utc")
    if entry.status == "RETIRED" and valid_until is None:
        raise ValueError("retired key records require valid_until_utc")
    if entry.status == "REVOKED" and revoked is None:
        raise ValueError("revoked key records require revoked_utc")
    if entry.status != "REVOKED" and revoked is not None:
        raise ValueError("revoked_utc is only valid for revoked key records")


def _registry_payload(registry: TrustRegistry | dict[str, Any]) -> dict[str, Any]:
    if isinstance(registry, TrustRegistry):
        payload = registry.model_dump(mode="json")
    else:
        payload = dict(registry)
    payload.pop("registry_digest", None)
    return payload


def build_trust_registry(
    *,
    registry_id: str,
    generated_utc: str,
    entries: list[TrustKeyRecord],
) -> TrustRegistry:
    _parse_utc(generated_utc)
    ordered = tuple(sorted(entries, key=lambda item: (*_entry_identity(item), item.valid_from_utc)))
    seen: set[tuple[str, str, str]] = set()
    for entry in ordered:
        _validate_entry(entry)
        identity = _entry_identity(entry)
        if identity in seen:
            raise ValueError("duplicate signer/key/algorithm record")
        seen.add(identity)

    payload: dict[str, Any] = {
        "schema": TRUST_REGISTRY_SCHEMA,
        "registry_id": registry_id,
        "generated_utc": generated_utc,
        "entries": [entry.model_dump(mode="json") for entry in ordered],
    }
    payload["registry_digest"] = _digest(payload)
    return TrustRegistry.model_validate(payload)


def verify_trust_registry(registry: TrustRegistry) -> bool:
    try:
        _parse_utc(registry.generated_utc)
        seen: set[tuple[str, str, str]] = set()
        for entry in registry.entries:
            _validate_entry(entry)
            identity = _entry_identity(entry)
            if identity in seen:
                return False
            seen.add(identity)
    except (TypeError, ValueError):
        return False
    return _digest(_registry_payload(registry)) == registry.registry_digest


def trust_record_for_attestation(
    attestation: ProvenanceAttestation,
    registry: TrustRegistry,
) -> TrustKeyRecord | None:
    if not verify_trust_registry(registry):
        return None

    matches = [
        entry
        for entry in registry.entries
        if entry.signer_id == attestation.signer_id
        and entry.key_id == attestation.key_id
        and entry.algorithm == attestation.algorithm
    ]
    if len(matches) != 1:
        return None

    entry = matches[0]
    if entry.status == "REVOKED":
        return None

    try:
        issued = _parse_utc(attestation.issued_utc)
        valid_from = _parse_utc(entry.valid_from_utc)
        valid_until = _parse_utc(entry.valid_until_utc) if entry.valid_until_utc else None
    except (TypeError, ValueError):
        return None

    if issued < valid_from:
        return None
    if valid_until is not None and issued > valid_until:
        return None
    return entry


def verify_attestation_with_registry(
    attestation: ProvenanceAttestation,
    *,
    registry: TrustRegistry,
    verifier: Verifier,
) -> bool:
    entry = trust_record_for_attestation(attestation, registry)
    if entry is None:
        return False
    return verify_provenance_attestation(
        attestation,
        verifier=verifier,
        trusted_signer_ids={entry.signer_id},
        trusted_key_ids={entry.key_id},
        trusted_algorithms={entry.algorithm},
    )
