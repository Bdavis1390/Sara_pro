"""Consensus-continuity model for heterogeneous digital-asset systems.

Read-only metadata and validation only. This module separates consensus
mechanism, consensus authentication, resource/Sybil proof, finality, and local
self-validation so account-level PQ progress cannot be mistaken for consensus
readiness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

CONSENSUS_FAMILIES = {
    "POW_NAKAMOTO",
    "POS",
    "POS_BFT",
    "DPOS",
    "NPOS",
    "BFT",
    "POA",
    "PROOF_OF_SPACE_TIME",
    "PROOF_OF_CAPACITY",
    "ROLLUP_SEQUENCER",
    "VALIDITY_PROOF",
    "FRAUD_PROOF",
    "HYBRID",
    "OTHER_NAMED",
}

RESOURCE_PROOFS = {
    "WORK",
    "STAKE",
    "AUTHORITY",
    "STORAGE_SPACE",
    "CAPACITY",
    "COVERAGE",
    "HISTORY_CLOCK",
    "VALIDITY_PROOF",
    "FRAUD_PROOF",
    "NONE",
    "HYBRID",
    "OTHER_NAMED",
}

LOCAL_VALIDATION_MODES = {
    "FULL_NODE_REEXECUTION",
    "FULL_NODE_RULE_VALIDATION",
    "LIGHT_CLIENT_PROOF",
    "COMMITTEE_ATTESTATION",
    "VALIDITY_PROOF_VERIFICATION",
    "FRAUD_PROOF_VERIFICATION",
    "TRUSTED_SIGNER",
    "HYBRID",
    "UNSPECIFIED",
}

KEY_AGILITY_STATES = {
    "UNKNOWN",
    "FIXED_CLASSICAL",
    "ROTATABLE_CLASSICAL",
    "PLUGGABLE_AUTH_ONLY",
    "PQ_NON_MAINNET",
    "PQ_MAINNET",
}

PQ_CONSENSUS_STATES = {"CLASSICAL_OR_UNPROVEN", "PQ_RESEARCH_OR_PARTIAL", "PQ_DEPLOYED"}


@dataclass(frozen=True)
class ConsensusEvidenceRef:
    label: str
    url: str
    claim: str


@dataclass(frozen=True)
class ConsensusContinuityProfile:
    subject_id: str
    consensus_family: str
    mechanism_name: str
    resource_proof: str
    finality_model: str
    participant_auth_primitive: str
    participant_key_agility: str
    local_validation_mode: str
    consensus_pq_state: str
    resource_proof_agility: str
    poc_subtype: str = ""
    evidence: tuple[ConsensusEvidenceRef, ...] = tuple()


@dataclass(frozen=True)
class ConsensusContinuityAssessment:
    valid: bool
    state: str
    self_validation_state: str
    pq_consensus_state: str
    issues: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_consensus(profile: ConsensusContinuityProfile) -> ConsensusContinuityAssessment:
    issues: list[str] = []

    if not profile.subject_id.strip():
        issues.append("subject_id must be non-empty")
    if profile.consensus_family not in CONSENSUS_FAMILIES:
        issues.append("consensus_family is not recognized")
    if not profile.mechanism_name.strip():
        issues.append("mechanism_name must be non-empty")
    if profile.resource_proof not in RESOURCE_PROOFS:
        issues.append("resource_proof is not recognized")
    if profile.local_validation_mode not in LOCAL_VALIDATION_MODES:
        issues.append("local_validation_mode is not recognized")
    if profile.participant_key_agility not in KEY_AGILITY_STATES:
        issues.append("participant_key_agility is not recognized")
    if profile.consensus_pq_state not in PQ_CONSENSUS_STATES:
        issues.append("consensus_pq_state is not recognized")
    if not profile.finality_model.strip():
        issues.append("finality_model must be non-empty")
    if not profile.resource_proof_agility.strip():
        issues.append("resource_proof_agility must be non-empty")

    # PoC is too ambiguous to be a standalone label. Capacity and Coverage are
    # materially different mechanisms and must be declared explicitly.
    if profile.resource_proof == "COVERAGE" and profile.poc_subtype != "PROOF_OF_COVERAGE":
        issues.append("coverage-based PoC requires poc_subtype=PROOF_OF_COVERAGE")
    if profile.resource_proof == "CAPACITY" and profile.poc_subtype != "PROOF_OF_CAPACITY":
        issues.append("capacity-based PoC requires poc_subtype=PROOF_OF_CAPACITY")
    if profile.poc_subtype and profile.poc_subtype not in {
        "PROOF_OF_COVERAGE",
        "PROOF_OF_CAPACITY",
        "OTHER_NAMED",
    }:
        issues.append("poc_subtype is not recognized")

    # Proof of History is an auxiliary cryptographic clock, not a complete
    # consensus family. It may support a PoS/BFT family via resource_proof.
    if profile.mechanism_name.strip().upper() in {"PROOF OF HISTORY", "POH"}:
        issues.append("Proof of History alone is not a complete consensus mechanism")
    if profile.resource_proof == "HISTORY_CLOCK" and profile.consensus_family not in {
        "POS_BFT",
        "HYBRID",
        "OTHER_NAMED",
    }:
        issues.append("HISTORY_CLOCK must be attached to an explicit consensus family")

    # Stake/authority/BFT systems depend on participant authentication. Resource
    # proofs alone are not enough to characterize their PQ exposure.
    if profile.consensus_family in {"POS", "POS_BFT", "DPOS", "NPOS", "BFT", "POA", "HYBRID"}:
        if not profile.participant_auth_primitive.strip():
            issues.append("participant authentication primitive must be documented")

    # A claim of deployed PQ consensus must be internally consistent with the
    # validator/participant authentication plane.
    if profile.consensus_pq_state == "PQ_DEPLOYED" and profile.participant_key_agility != "PQ_MAINNET":
        issues.append("PQ_DEPLOYED requires PQ_MAINNET participant-key agility")

    if not profile.evidence:
        issues.append("at least one consensus evidence reference is required")
    for index, item in enumerate(profile.evidence):
        if not (item.label.strip() and item.claim.strip() and item.url.startswith("https://")):
            issues.append(f"evidence[{index}] must include label, HTTPS URL, and claim")

    if profile.local_validation_mode == "UNSPECIFIED":
        self_validation = "SELF_VALIDATION_NOT_ESTABLISHED"
    elif profile.local_validation_mode in {
        "FULL_NODE_REEXECUTION",
        "FULL_NODE_RULE_VALIDATION",
        "LIGHT_CLIENT_PROOF",
        "VALIDITY_PROOF_VERIFICATION",
        "FRAUD_PROOF_VERIFICATION",
        "HYBRID",
    }:
        self_validation = "SELF_VALIDATION_DOCUMENTED"
    else:
        self_validation = "EXTERNAL_OR_COMMITTEE_VALIDATION_DOCUMENTED"

    if issues:
        state = "CONSENSUS_CONTINUITY_INVALID"
    elif profile.consensus_pq_state == "PQ_DEPLOYED":
        state = "CONSENSUS_PQ_DEPLOYED"
    elif profile.consensus_pq_state == "PQ_RESEARCH_OR_PARTIAL":
        state = "CONSENSUS_PQ_MIGRATION_PARTIAL"
    else:
        state = "CONSENSUS_CLASSICAL_OR_UNPROVEN"

    return ConsensusContinuityAssessment(
        valid=not issues,
        state=state,
        self_validation_state=self_validation,
        pq_consensus_state=profile.consensus_pq_state,
        issues=tuple(issues),
    )
