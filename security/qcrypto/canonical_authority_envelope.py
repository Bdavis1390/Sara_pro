"""Canonical cross-chain authority envelope for defensive PQ migration.

This is a protocol-neutral control contract. Chain adapters can map native rekey,
address aliases, programmable validators, or other supported mechanisms into the
same governance model. It performs no signing, key generation, or asset movement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CanonicalAuthorityEnvelope:
    chain: str
    adapter_class: str
    stable_authority_id: bool = False
    authenticator_versioned: bool = False
    authenticator_replaceable: bool = False
    policy_versioned: bool = False
    recovery_commitment_present: bool = False
    chain_binding_present: bool = False
    replay_domain_present: bool = False
    evidence_binding_present: bool = False
    explicit_human_approval_required: bool = True
    live_chain_support: bool = False
    independent_review_complete: bool = False
    consensus_layer_pq: bool = False


@dataclass(frozen=True)
class CanonicalAuthorityAssessment:
    adapter_state: str
    governance_state: str
    migration_state: str
    action: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_canonical_authority_envelope(profile: CanonicalAuthorityEnvelope) -> CanonicalAuthorityAssessment:
    blockers: list[str] = []

    core = all(
        (
            profile.stable_authority_id,
            profile.authenticator_versioned,
            profile.authenticator_replaceable,
            profile.policy_versioned,
            profile.recovery_commitment_present,
            profile.chain_binding_present,
            profile.replay_domain_present,
            profile.evidence_binding_present,
        )
    )

    if core and profile.live_chain_support:
        adapter_state = "CHAIN_ADAPTER_CONTRACT_SATISFIED"
    elif core:
        adapter_state = "ADAPTER_CONTRACT_READY_CHAIN_ACTIVATION_PENDING"
    else:
        adapter_state = "ADAPTER_CONTRACT_INCOMPLETE"
        blockers.append("Stable identity, versioned replaceable authentication, policy, recovery, chain binding, replay domain, and evidence binding are all required.")

    if profile.explicit_human_approval_required and profile.policy_versioned and profile.evidence_binding_present:
        governance_state = "HUMAN_GATED_VERSIONED_GOVERNANCE"
    else:
        governance_state = "GOVERNANCE_GAPS_PRESENT"
        blockers.append("Explicit approval, policy versioning, and evidence binding must remain mandatory.")

    if adapter_state == "CHAIN_ADAPTER_CONTRACT_SATISFIED" and profile.independent_review_complete:
        migration_state = "CANONICAL_AUTHORITY_ADAPTER_PILOT_READY"
        action = "USE_ONLY_WITH_CHAIN_SPECIFIC_BOUNDED_CANARY_AND_SEPARATE_EXECUTION_APPROVAL"
    elif adapter_state == "CHAIN_ADAPTER_CONTRACT_SATISFIED":
        migration_state = "CANONICAL_AUTHORITY_ADAPTER_REVIEW_REQUIRED"
        action = "COMPLETE_INDEPENDENT_REVIEW_BEFORE_PILOT_PROMOTION"
    elif adapter_state == "ADAPTER_CONTRACT_READY_CHAIN_ACTIVATION_PENDING":
        migration_state = "CANONICAL_AUTHORITY_ADAPTER_WAITING_ON_CHAIN"
        action = "PRESERVE_INTERFACE_AND_VALIDATE_WHEN_CHAIN_CAPABILITY_ACTIVATES"
    else:
        migration_state = "CANONICAL_AUTHORITY_ADAPTER_DESIGN"
        action = "COMPLETE_REQUIRED_CONTROL_BINDINGS"

    if not profile.consensus_layer_pq:
        blockers.append("Authority-envelope readiness does not imply post-quantum consensus or validator security.")

    return CanonicalAuthorityAssessment(
        adapter_state=adapter_state,
        governance_state=governance_state,
        migration_state=migration_state,
        action=action,
        blockers=tuple(blockers),
    )
