"""Fail-closed source-lock validation for WS-QBENCH-MGRAPH v0.5."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXACT_REPRODUCTION_GAPS = {
    "G1_effective_zero_connected_loop",
    "G2_figure4ef_hamiltonian_normalization",
    "G3_random_subgraph_duplicate_policy",
    "G4_author_code",
}


class SourceLockError(RuntimeError):
    pass


def _canonical_without_digest(payload: dict[str, Any]) -> bytes:
    body = dict(payload)
    body.pop("lock_digest_sha256", None)
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_lock_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_without_digest(payload)).hexdigest()


def load_source_lock(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    validate_source_lock(payload)
    return payload


def unresolved_exact_reproduction_gaps(payload: dict[str, Any]) -> list[str]:
    gaps = payload.get("gaps", {})
    return sorted(
        key
        for key in EXACT_REPRODUCTION_GAPS
        if gaps.get(key, {}).get("status") != "locked"
    )


def validate_source_lock(payload: dict[str, Any]) -> None:
    if payload.get("schema") != "ws-qbench-mgraph/source-lock-v0.5":
        raise SourceLockError("unexpected or missing source-lock schema")

    stored = payload.get("lock_digest_sha256")
    if not isinstance(stored, str) or len(stored) != 64:
        raise SourceLockError("missing or malformed source-lock digest")
    computed = compute_lock_digest(payload)
    if computed != stored:
        raise SourceLockError("source-lock digest mismatch")

    gaps = payload.get("gaps")
    if not isinstance(gaps, dict):
        raise SourceLockError("gaps must be an object")

    missing = EXACT_REPRODUCTION_GAPS.difference(gaps)
    if missing:
        raise SourceLockError(f"required source-lock gaps missing: {sorted(missing)}")

    policy = payload.get("claims_policy", {})
    unresolved = unresolved_exact_reproduction_gaps(payload)
    if unresolved and policy.get("exact_figure_reproduction_allowed") is True:
        raise SourceLockError(
            "exact figure reproduction cannot be enabled while source-lock gaps remain unresolved"
        )
    if policy.get("hardware_inference_allowed") is True:
        raise SourceLockError("hardware inference is outside the v0.5 claims ceiling")


def authorize_exact_figure_reproduction(payload: dict[str, Any]) -> None:
    """Raise unless all source-lock blockers are explicitly locked."""
    validate_source_lock(payload)
    unresolved = unresolved_exact_reproduction_gaps(payload)
    if unresolved:
        raise SourceLockError(
            "exact reproduction blocked by unresolved source-lock gaps: "
            + ", ".join(unresolved)
        )
