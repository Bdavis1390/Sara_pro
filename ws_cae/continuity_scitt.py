"""SCITT-oriented transparency statements for WS-CAE continuity manifests.

Serialization only. This module does not create keys, sign, register statements,
or perform cryptocurrency operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

MEDIA_TYPE = "application/vnd.ws-cae.cryptographic-continuity+json"
SPEC = "WS-CAE-SCITT-CONTINUITY-1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_statement(envelope: dict[str, Any], issuer: str, observed_at: str | None = None) -> dict[str, Any]:
    if envelope.get("spec") != "WS-CAE-CONTINUITY-MANIFEST-1":
        raise ValueError("unsupported continuity manifest spec")
    if not envelope.get("valid"):
        raise ValueError("continuity manifest must be valid")
    content_id = str(envelope.get("content_id", ""))
    if not content_id.startswith("sha256:"):
        raise ValueError("continuity manifest requires sha256 content_id")
    manifest = envelope.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("continuity manifest payload is missing")
    issuer = issuer.strip()
    if not issuer:
        raise ValueError("issuer must be non-empty")

    return {
        "spec": SPEC,
        "media_type": MEDIA_TYPE,
        "issuer": issuer,
        "observed_at": observed_at or _utc_now(),
        "subject": {
            "id": manifest.get("subject_id"),
            "type": manifest.get("subject_type"),
            "content_id": content_id,
            "version": manifest.get("version"),
            "as_of": manifest.get("as_of"),
        },
        "claims": {
            "authority_model": manifest.get("authority_model"),
            "implementation_maturity": manifest.get("implementation_maturity"),
            "protocol_commitment_state": manifest.get("protocol_commitment_state"),
            "pq_authorization_state": manifest.get("pq_authorization_state"),
            "consensus_pq_state": manifest.get("consensus_pq_state"),
            "crypto_agility_state": manifest.get("crypto_agility_state"),
            "recovery_state": manifest.get("recovery_state"),
        },
        "dependencies": manifest.get("dependencies", []),
        "evidence": manifest.get("evidence", []),
    }
