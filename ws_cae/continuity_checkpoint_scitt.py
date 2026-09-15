"""SCITT-oriented statement serializer for continuity transparency checkpoints.

Serialization only; no signing, registration, consensus, tokens, or asset actions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .continuity_checkpoint import LinkedCheckpoint
from .continuity_validation import valid_content_id, valid_datetime

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
    if not valid_content_id(checkpoint.root_hash):
        raise ValueError("checkpoint root must be a canonical lowercase SHA-256 content identifier")
    linked = checkpoint.previous_tree_size is not None or checkpoint.previous_root_hash is not None
    if linked and (checkpoint.previous_tree_size is None or checkpoint.previous_root_hash is None):
        raise ValueError("checkpoint predecessor metadata must be complete")
    if checkpoint.previous_tree_size is not None and checkpoint.previous_tree_size < 0:
        raise ValueError("previous_tree_size must be non-negative")
    if checkpoint.previous_root_hash is not None and not valid_content_id(checkpoint.previous_root_hash):
        raise ValueError("previous checkpoint root must be a canonical lowercase SHA-256 content identifier")
    timestamp = observed_at or _now()
    if not valid_datetime(timestamp):
        raise ValueError("observed_at must be a timezone-aware ISO-8601 datetime")
    return {
        "spec": SPEC,
        "media_type": MEDIA_TYPE,
        "issuer": issuer,
        "observed_at": timestamp,
        "checkpoint": checkpoint.to_dict(),
    }
