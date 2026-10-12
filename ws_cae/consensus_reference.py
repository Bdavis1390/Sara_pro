"""Create a read-only dependency reference for a consensus-continuity profile."""

from __future__ import annotations

from .consensus_continuity import ConsensusContinuityProfile, assess_consensus, content_id
from .continuity_manifest import DependencyRef


def consensus_dependency(profile: ConsensusContinuityProfile) -> DependencyRef:
    result = assess_consensus(profile)
    return DependencyRef(
        role="CONSENSUS_CONTINUITY",
        subject=content_id(profile),
        critical=True,
        readiness_state=result.state,
    )
