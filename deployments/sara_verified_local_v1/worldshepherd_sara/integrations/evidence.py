from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


EVIDENCE_ENVELOPE_SCHEMA_VERSION = "1.0"


def canonical_config_digest(config: Mapping[str, Any]) -> str:
    """Return a deterministic SHA-256 digest for JSON-compatible configuration.

    The configuration itself is not retained in the evidence envelope. This keeps
    the primitive suitable for provenance without encouraging secrets or runtime
    credentials to be copied into evidence records.
    """

    encoded = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


@dataclass(frozen=True)
class EvidenceEnvelope:
    schema_version: str
    integration_id: str
    surface: str
    claim_status: str
    config_digest: str
    evidence_refs: tuple[str, ...]
    operator_authorization_ref: str | None
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        integration_id: str,
        surface: str,
        claim_status: str,
        config: Mapping[str, Any],
        evidence_refs: Sequence[str] = (),
        operator_authorization_ref: str | None = None,
    ) -> "EvidenceEnvelope":
        if not integration_id.strip():
            raise ValueError("integration_id must not be empty")
        if not surface.strip():
            raise ValueError("surface must not be empty")
        if not claim_status.strip():
            raise ValueError("claim_status must not be empty")

        refs = tuple(ref.strip() for ref in evidence_refs if ref.strip())
        auth_ref = (
            operator_authorization_ref.strip()
            if operator_authorization_ref and operator_authorization_ref.strip()
            else None
        )
        return cls(
            schema_version=EVIDENCE_ENVELOPE_SCHEMA_VERSION,
            integration_id=integration_id,
            surface=surface,
            claim_status=claim_status,
            config_digest=canonical_config_digest(config),
            evidence_refs=refs,
            operator_authorization_ref=auth_ref,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
