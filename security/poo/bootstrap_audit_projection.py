"""Claims-controlled audit projection for the one-time PoO technical-registry bootstrap.

Bootstrap is not a normal lineage operation: before genesis there is intentionally no
active tip. This projection therefore has its own schema and records only an empty-
registry initialization decision. It never authorizes legal title, credential rotation,
live-value movement, or external transfer execution.
"""

from __future__ import annotations

from typing import Dict

from security.poo.bootstrap_governance_guard import GovernedBootstrapCommitDecision


POO_BOOTSTRAP_AUDIT_SCHEMA = "WS-POO-BOOTSTRAP-COMMIT-DECISION-V1"
POO_BOOTSTRAP_CLAIM_BOUNDARY = "INTERNAL_POO_EMPTY_REGISTRY_BOOTSTRAP_ONLY"


def bootstrap_commit_readiness_audit_projection(
    decision: GovernedBootstrapCommitDecision,
    *,
    asset_id: str,
) -> Dict[str, object]:
    if decision.ready:
        states = (
            "ECHO_POO_BOOTSTRAP_EVIDENCE_ACCEPTED",
            "PRIME_POO_BOOTSTRAP_COMMIT_CANDIDATE_READY",
            "SARA_POO_BOOTSTRAP_HUMAN_REVIEW_READY",
            "OVERWATCH_POO_BOOTSTRAP_PENDING",
        )
    elif not decision.empty_registry_verified:
        states = (
            "ECHO_POO_BOOTSTRAP_NONEMPTY_RECORDED",
            "PRIME_POO_BOOTSTRAP_PERMANENTLY_BLOCKED",
            "SARA_POO_BOOTSTRAP_BLOCKED",
            "OVERWATCH_POO_BOOTSTRAP_REJECTED",
        )
    elif not decision.optimistic_concurrency_match:
        states = (
            "ECHO_POO_BOOTSTRAP_STALE_SNAPSHOT_RECORDED",
            "PRIME_POO_BOOTSTRAP_BLOCKED_STALE",
            "SARA_POO_BOOTSTRAP_REEVALUATION_REQUIRED",
            "OVERWATCH_POO_BOOTSTRAP_STALE_SNAPSHOT_ALERT",
        )
    else:
        states = (
            "ECHO_POO_BOOTSTRAP_EVIDENCE_INCOMPLETE",
            "PRIME_POO_BOOTSTRAP_BLOCKED",
            "SARA_POO_BOOTSTRAP_BLOCKED",
            "OVERWATCH_POO_BOOTSTRAP_REVIEW_REQUIRED",
        )

    return {
        "schema": POO_BOOTSTRAP_AUDIT_SCHEMA,
        "operation": "REGISTRY_BOOTSTRAP_COMMIT_READINESS",
        "asset_id": asset_id,
        "source_digest": decision.digest,
        "source_status": decision.status,
        "echo_state": states[0],
        "prime_state": states[1],
        "sara_state": states[2],
        "overwatch_state": states[3],
        "empty_registry_verified": decision.empty_registry_verified,
        "ownership_evidence_ready": decision.ownership_evidence_ready,
        "coc_valid": decision.coc_valid,
        "state_transition_ready": decision.state_transition_ready,
        "registry_commit_ready": decision.ready,
        "optimistic_concurrency_checked": decision.optimistic_concurrency_checked,
        "optimistic_concurrency_match": decision.optimistic_concurrency_match,
        "expected_registry_digest": decision.expected_registry_digest,
        "current_registry_digest": decision.current_registry_digest,
        "candidate_registry_digest": decision.candidate_registry_digest,
        "candidate_state_digest": decision.candidate_state_digest,
        "human_approval_required": True,
        "technical_registry_committed": False,
        "durable_registry_write_authorized": False,
        "legal_title_established": False,
        "legal_title_changed": False,
        "live_value_moved": False,
        "credential_rotated": False,
        "external_transfer_executed": False,
        "claim_boundary": POO_BOOTSTRAP_CLAIM_BOUNDARY,
    }
