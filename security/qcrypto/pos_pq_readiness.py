"""Fail-closed post-quantum readiness classification for stake-based consensus.

This module prevents isolated post-quantum signature interoperability from being
misrepresented as production post-quantum consensus readiness. Evidence is split
across system dependencies and graded by the environment in which it has actually
been demonstrated.

No network action is performed here. The classifier is claims-control software.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Mapping

from security.qcrypto.pos_family_preservation import PROFILES
from security.qcrypto.pos_pq_benchmarks import BENCHMARKS


class EvidenceTier(IntEnum):
    NONE = 0
    INTERNAL_INTEROP = 1
    EXTERNAL_DESIGN = 2
    PUBLIC_TESTNET = 3
    PRODUCTION = 4


AXES = (
    "consensus_signature_acceptance",
    "leader_election_or_randomness",
    "aggregation_or_finality",
    "node_identity_or_transport",
    "economic_owner_or_governance_auth",
    "protocol_client_support",
    "operational_key_lifecycle",
)


@dataclass(frozen=True)
class ReadinessEvidence:
    profile_id: str
    evidence: tuple[tuple[str, EvidenceTier], ...]
    external_state: str
    notes: tuple[str, ...] = ()

    def evidence_map(self) -> dict[str, EvidenceTier]:
        return dict(self.evidence)


@dataclass(frozen=True)
class ReadinessAssessment:
    profile_id: str
    classification: str
    production_ready: bool
    minimum_tier: str
    blocking_axes: tuple[str, ...]
    evidence: tuple[tuple[str, str], ...]
    external_state: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blocking_axes"] = list(self.blocking_axes)
        data["evidence"] = [list(item) for item in self.evidence]
        data["notes"] = list(self.notes)
        return data


def _evidence(
    profile_id: str,
    *,
    consensus_signature_acceptance: EvidenceTier = EvidenceTier.INTERNAL_INTEROP,
    leader_election_or_randomness: EvidenceTier = EvidenceTier.NONE,
    aggregation_or_finality: EvidenceTier = EvidenceTier.NONE,
    node_identity_or_transport: EvidenceTier = EvidenceTier.NONE,
    economic_owner_or_governance_auth: EvidenceTier = EvidenceTier.NONE,
    protocol_client_support: EvidenceTier = EvidenceTier.NONE,
    operational_key_lifecycle: EvidenceTier = EvidenceTier.NONE,
    external_state: str,
    notes: tuple[str, ...] = (),
) -> ReadinessEvidence:
    values = {
        "consensus_signature_acceptance": consensus_signature_acceptance,
        "leader_election_or_randomness": leader_election_or_randomness,
        "aggregation_or_finality": aggregation_or_finality,
        "node_identity_or_transport": node_identity_or_transport,
        "economic_owner_or_governance_auth": economic_owner_or_governance_auth,
        "protocol_client_support": protocol_client_support,
        "operational_key_lifecycle": operational_key_lifecycle,
    }
    return ReadinessEvidence(
        profile_id=profile_id,
        evidence=tuple((axis, values[axis]) for axis in AXES),
        external_state=external_state,
        notes=notes,
    )


# Internal ML-DSA/SLH-DSA envelope interoperability is intentionally recorded at
# INTERNAL_INTEROP only. It does not imply that the corresponding production
# protocol accepts those signatures.
TARGET_EVIDENCE: dict[str, ReadinessEvidence] = {
    profile_id: _evidence(
        profile_id,
        external_state="NO_EXTERNAL_PRODUCTION_PQ_CONSENSUS_EVIDENCE_RECORDED",
        notes=("Worldshepherd family-bound PQ signature interoperability is internal evidence only.",),
    )
    for profile_id in PROFILES
}

# Ethereum has official external development/roadmap evidence, but not production
# PQ consensus acceptance. The production-readiness result remains fail-closed.
TARGET_EVIDENCE["ETHEREUM"] = _evidence(
    "ETHEREUM",
    consensus_signature_acceptance=EvidenceTier.EXTERNAL_DESIGN,
    aggregation_or_finality=EvidenceTier.EXTERNAL_DESIGN,
    protocol_client_support=EvidenceTier.EXTERNAL_DESIGN,
    external_state="OFFICIAL_PQ_CONSENSUS_ROADMAP_ACTIVE_PRODUCTION_TRANSITION_INCOMPLETE",
    notes=(
        "External design/development evidence does not equal production signature acceptance.",
        "Leader election/finality/networking/operations must be re-evidenced at deployment grade.",
    ),
)

# Algorand's production PQ account authorization is meaningful, but official
# material reviewed for this project says consensus participation keys were not
# changed by that account feature. Therefore only the economic/account-auth axis
# receives production-component evidence.
TARGET_EVIDENCE["ALGORAND"] = _evidence(
    "ALGORAND",
    consensus_signature_acceptance=EvidenceTier.INTERNAL_INTEROP,
    economic_owner_or_governance_auth=EvidenceTier.PRODUCTION,
    external_state="PRODUCTION_PQ_ACCOUNT_AUTH_COMPONENT_CONSENSUS_PARTICIPATION_UNCHANGED",
    notes=(
        "Production PQ account authorization must not be promoted to PQ consensus readiness.",
    ),
)


BENCHMARK_EVIDENCE: dict[str, ReadinessEvidence] = {
    "QRL2_TESTNET": _evidence(
        "QRL2_TESTNET",
        consensus_signature_acceptance=EvidenceTier.PUBLIC_TESTNET,
        protocol_client_support=EvidenceTier.PUBLIC_TESTNET,
        external_state="PUBLIC_TESTNET_ML_DSA_STAKING_VALIDATOR_AUTHENTICATION",
        notes=(
            "Official QRL 2.0 Testnet V2 material requires ML-DSA for staking validators.",
            "Testnet evidence is not production-mainnet evidence.",
            "Unverified system axes remain blockers for a full-system PQ claim.",
        ),
    )
}


def validate_evidence(record: ReadinessEvidence) -> None:
    values = record.evidence_map()
    if tuple(values) != AXES:
        raise ValueError("readiness evidence must contain every axis exactly once in canonical order")
    if not record.external_state:
        raise ValueError("external_state is required")


def assess(record: ReadinessEvidence) -> ReadinessAssessment:
    validate_evidence(record)
    values = record.evidence_map()
    blocking = tuple(axis for axis in AXES if values[axis] < EvidenceTier.PRODUCTION)
    production_ready = not blocking
    minimum = min(values.values())

    if production_ready:
        classification = "PRODUCTION_PQ_CONSENSUS_READY"
    elif (
        values["consensus_signature_acceptance"] >= EvidenceTier.PUBLIC_TESTNET
        and values["protocol_client_support"] >= EvidenceTier.PUBLIC_TESTNET
    ):
        classification = "PUBLIC_PQ_VALIDATOR_AUTH_TESTNET"
    elif any(value is EvidenceTier.PRODUCTION for value in values.values()):
        classification = "PRODUCTION_PQ_COMPONENT_ONLY"
    elif any(value is EvidenceTier.EXTERNAL_DESIGN for value in values.values()):
        classification = "PQ_TRANSITION_IN_EXTERNAL_DEVELOPMENT"
    elif any(value is EvidenceTier.INTERNAL_INTEROP for value in values.values()):
        classification = "INTERNAL_PQ_INTEROP_ONLY"
    else:
        classification = "NO_PQ_EVIDENCE"

    return ReadinessAssessment(
        profile_id=record.profile_id,
        classification=classification,
        production_ready=production_ready,
        minimum_tier=minimum.name,
        blocking_axes=blocking,
        evidence=tuple((axis, values[axis].name) for axis in AXES),
        external_state=record.external_state,
        notes=record.notes,
    )


def assess_all_targets() -> dict[str, ReadinessAssessment]:
    return {profile_id: assess(record) for profile_id, record in TARGET_EVIDENCE.items()}


def assess_all_benchmarks() -> dict[str, ReadinessAssessment]:
    return {profile_id: assess(record) for profile_id, record in BENCHMARK_EVIDENCE.items()}


def assert_fail_closed_claims() -> None:
    targets = assess_all_targets()
    if set(targets) != set(PROFILES):
        raise AssertionError("every PoS target profile must have an explicit readiness record")
    wrongly_ready = [profile_id for profile_id, result in targets.items() if result.production_ready]
    if wrongly_ready:
        raise AssertionError(f"production PQ readiness is not externally established for: {wrongly_ready}")

    benchmarks = assess_all_benchmarks()
    if set(benchmarks) != set(BENCHMARKS):
        raise AssertionError("every external benchmark must have an explicit readiness record")
    for benchmark_id, result in benchmarks.items():
        if result.production_ready:
            raise AssertionError(f"testnet benchmark was improperly promoted to production: {benchmark_id}")
