"""RFC 9943-oriented statement payloads for WS-CAE metadata.

This module only serializes already-observed authority/readiness metadata into a
stable JSON payload suitable for signing and registration by a SCITT issuer.
It does not create keys, sign statements, submit to a transparency service, or
perform any cryptocurrency transaction.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

MEDIA_TYPE = "application/vnd.ws-cae.digital-asset-authority+json"
SPEC = "WS-CAE-SCITT-STATEMENT-1"


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for hashing and transport."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_chain_statement(patch: dict[str, Any], issuer: str, observed_at: str | None = None) -> dict[str, Any]:
    """Build a signed-statement payload from a WS-CAE chain patch.

    The output is intentionally issuer-neutral. A SCITT implementation may wrap
    these bytes in its supported COSE/CWT envelope and register the signed
    statement with a transparency service under its own policy.
    """
    chain = str(patch.get("chain", "")).strip()
    profile = patch.get("profile")
    evidence = patch.get("evidence")
    if not chain:
        raise ValueError("chain must be non-empty")
    if not isinstance(profile, dict):
        raise ValueError("profile must be an object")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("evidence must be a non-empty list")
    issuer = issuer.strip()
    if not issuer:
        raise ValueError("issuer must be non-empty")

    return {
        "spec": SPEC,
        "media_type": MEDIA_TYPE,
        "issuer": issuer,
        "observed_at": observed_at or _utc_now(),
        "subject": {
            "type": "blockchain-authority-state",
            "name": chain,
            "source_patch_sha256": sha256_hex(patch),
        },
        "claims": {
            "implementation_maturity": profile.get("implementation_maturity"),
            "protocol_commitment_state": profile.get("protocol_commitment_state"),
            "pq_authorization_state": profile.get("pq_authorization_state"),
            "consensus_pq_state": profile.get("consensus_pq_state"),
            "stable_authority_id": profile.get("stable_authority_id"),
            "authenticator_replaceable": profile.get("authenticator_replaceable"),
            "recovery_state_documented": profile.get("recovery_state_documented"),
            "policy_state_documented": profile.get("policy_state_documented"),
        },
        "evidence": evidence,
    }
