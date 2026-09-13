"""SCITT-oriented statement serializer for continuity transparency checkpoints.

Serialization only; no signing, registration, consensus, tokens, or asset actions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .continuity_checkpoint import LinkedCheckpoint

SPEC = "WS-CAE-SCITT-CONTINUITY-CHECKPOINT-1"
MEDIA_TYPE = "application/vnd.ws-cae.continuity-checkpoint+json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_checkpoint_statement(
    checkpoint: LinkedCheckpoint,
    issuer: str,
    observed_at: str | None = None,
) -> dict:
    issuer = issuer.strip()
    if not issuer:
        raise ValueError("issuer must be non-empty")
    if checkpoint.tree_size < 0:
        raise ValueError("tree_size must be non-negative")
    if not checkpoint.root_hash.startswith("sha256:"):
        raise ValueError("checkpoint root must use sha256 content form")
    linked = checkpoint.previous_tree_size is not None or checkpoint.previous_root_hash is not None
    if linked and (checkpoint.previous_tree_size is None or checkpoint.previous_root_hash is None):
        raise ValueError("checkpoint predecessor metadata must be complete")
    return {
        "spec": SPEC,
        "media_type": MEDIA_TYPE,
        "issuer": issuer,
        "observed_at": observed_at or _now(),
        "checkpoint": checkpoint.to_dict(),
    }
