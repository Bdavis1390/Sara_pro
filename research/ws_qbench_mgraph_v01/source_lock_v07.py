"""Fail-closed source-lock validation for WS-QBENCH-MGRAPH v0.7."""

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


def unresolved_exact_reproduction_gaps(payload: dict[str, Any]) -> list[str]:
    gaps = payload.get("gaps", {})
    return sorted(
        key
        for key in EXACT_REPRODUCTION_GAPS
        if gaps.get(key, {}).get("status") != "locked"
    )


def validate_source_lock(payload: dict[str, Any]) -> None:
    if payload.get("schema") != "ws-qbench-mgraph/source-lock-v0.7":
        raise SourceLockError("unexpected or missing source-lock schema")

    stored = payload.get("lock_digest_sha256")
    if not isinstance(stored, str) or len(stored) != 64:
        raise SourceLockError("missing or malformed source-lock digest")
    if compute_lock_digest(payload) != stored:
        raise SourceLockError("source-lock digest mismatch")

    gaps = payload.get("gaps")
    if not isinstance(gaps, dict):
        raise SourceLockError("gaps must be an object")
    missing = EXACT_REPRODUCTION_GAPS.difference(gaps)
    if missing:
        raise SourceLockError(f"required source-lock gaps missing: {sorted(missing)}")

    clarification = payload.get("author_clarification")
    if not isinstance(clarification, dict):
        raise SourceLockError("author clarification provenance is required")
    if clarification.get("corresponding_author") != "Sunkyu Yu":
        raise SourceLockError("unexpected corresponding-author provenance")

    conventions = payload.get("locked_conventions", {})
    if conventions.get("Nmax") != 200:
        raise SourceLockError("author-locked Nmax must remain 200")
    if conventions.get("random_realizations") != 20000:
        raise SourceLockError("author-locked realization count must remain 20000")
    if conventions.get("random_subgraph_sampling") != "without replacement":
        raise SourceLockError("author-locked sampling policy changed")

    policy = payload.get("claims_policy", {})
    unresolved = unresolved_exact_reproduction_gaps(payload)
    if unresolved and policy.get("exact_figure_reproduction_allowed") is True:
        raise SourceLockError(
            "exact figure reproduction cannot be enabled while source-lock gaps remain unresolved"
        )
    if policy.get("hardware_inference_allowed") is True:
        raise SourceLockError("hardware inference is outside the source-lock claims ceiling")


def load_source_lock(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_source_lock(payload)
    return payload


def authorize_exact_figure_reproduction(payload: dict[str, Any]) -> None:
    validate_source_lock(payload)
    unresolved = unresolved_exact_reproduction_gaps(payload)
    if unresolved:
        raise SourceLockError(
            "exact reproduction blocked by unresolved source-lock gaps: "
            + ", ".join(unresolved)
        )
