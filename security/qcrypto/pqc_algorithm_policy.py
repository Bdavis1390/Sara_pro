"""Fail-closed post-quantum algorithm lifecycle and agility policy.

This module is a claims-control layer. It does not implement cryptographic
algorithms, generate keys, sign data, decapsulate ciphertexts, or modify live
systems. It records whether an algorithm is standards-eligible for a role and
whether deployment evidence is strong enough for a bounded environment claim.

The policy deliberately separates:

* NIST standardization state;
* cryptographic role compatibility;
* deployment/protocol support;
* evidence freshness; and
* Worldshepherd transition posture.

A finalized PQC standard is not automatically production-ready in every
protocol. Conversely, an algorithm selected for future standardization is not
promoted to the same state as a published FIPS.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import IntEnum, StrEnum


class StandardizationState(StrEnum):
    FINAL_FIPS = "FINAL_FIPS"
    SELECTED_FOR_STANDARDIZATION = "SELECTED_FOR_STANDARDIZATION"
    FIPS_IN_DEVELOPMENT = "FIPS_IN_DEVELOPMENT"
    WITHDRAWN = "WITHDRAWN"
    CLASSICAL_STANDARD = "CLASSICAL_STANDARD"


class CryptoRole(StrEnum):
    KEY_ESTABLISHMENT = "KEY_ESTABLISHMENT"
    DIGITAL_SIGNATURE = "DIGITAL_SIGNATURE"
    CONSENSUS_AUTH = "CONSENSUS_AUTH"
    NODE_IDENTITY = "NODE_IDENTITY"


class Environment(StrEnum):
    LAB = "LAB"
    TESTNET = "TESTNET"
    PRODUCTION = "PRODUCTION"


class SupportTier(IntEnum):
    NONE = 0
    INTERNAL = 1
    PUBLIC_TESTNET = 2
    PRODUCTION = 3


class TransitionMode(StrEnum):
    PQ_ONLY = "PQ_ONLY"
    HYBRID_TRANSITION = "HYBRID_TRANSITION"
    CLASSICAL_ONLY = "CLASSICAL_ONLY"


@dataclass(frozen=True)
class AlgorithmPolicy:
    algorithm_id: str
    display_name: str
    standardization_state: StandardizationState
    standard_reference: str
    pq_resistant: bool
    roles: tuple[CryptoRole, ...]
    source_urls: tuple[str, ...]
    evidence_as_of: date
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AlgorithmRequest:
    algorithm_id: str
    role: CryptoRole
    environment: Environment
    support_tier: SupportTier
    transition_mode: TransitionMode
    evidence_checked_on: date
    max_evidence_age_days: int = 120


@dataclass(frozen=True)
class AlgorithmDecision:
    algorithm_id: str
    verdict: str
    standards_eligible: bool
    deployment_eligible: bool
    pq_posture: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    standardization_state: str
    standard_reference: str
    role: str
    environment: str
    support_tier: str
    transition_mode: str
    claim_boundary: str = (
        "Algorithm-policy classification only; this does not establish FIPS module "
        "validation, protocol conformance, production deployment, Federal compliance, "
        "or end-to-end post-quantum security."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


NIST_PQC = "https://www.nist.gov/pqc"
NIST_FIPS_203 = "https://csrc.nist.gov/pubs/fips/203/final"
NIST_FIPS_204 = "https://csrc.nist.gov/pubs/fips/204/final"
NIST_FIPS_205 = "https://csrc.nist.gov/pubs/fips/205/final"
NIST_PQC_STANDARDIZATION = (
    "https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/"
    "Post_Quantum_Cryptography-Standardization"
)
NIST_HQC = (
    "https://www.nist.gov/news-events/news/2025/03/"
    "nist-selects-hqc-fifth-algorithm-post-quantum-encryption"
)


REGISTRY: dict[str, AlgorithmPolicy] = {
    "ML-KEM": AlgorithmPolicy(
        algorithm_id="ML-KEM",
        display_name="Module-Lattice-Based Key-Encapsulation Mechanism",
        standardization_state=StandardizationState.FINAL_FIPS,
        standard_reference="FIPS 203",
        pq_resistant=True,
        roles=(CryptoRole.KEY_ESTABLISHMENT,),
        source_urls=(NIST_FIPS_203, NIST_PQC),
        evidence_as_of=date(2026, 9, 15),
    ),
    "ML-DSA": AlgorithmPolicy(
        algorithm_id="ML-DSA",
        display_name="Module-Lattice-Based Digital Signature Algorithm",
        standardization_state=StandardizationState.FINAL_FIPS,
        standard_reference="FIPS 204",
        pq_resistant=True,
        roles=(CryptoRole.DIGITAL_SIGNATURE, CryptoRole.CONSENSUS_AUTH, CryptoRole.NODE_IDENTITY),
        source_urls=(NIST_FIPS_204, NIST_PQC),
        evidence_as_of=date(2026, 9, 15),
        notes=(
            "FIPS standardization does not imply that a target consensus or identity protocol accepts ML-DSA.",
            "FIPS 204 has a 2026 planning-note errata list; implementation evidence must identify the exact revision/interpretation used.",
        ),
    ),
    "SLH-DSA": AlgorithmPolicy(
        algorithm_id="SLH-DSA",
        display_name="Stateless Hash-Based Digital Signature Algorithm",
        standardization_state=StandardizationState.FINAL_FIPS,
        standard_reference="FIPS 205",
        pq_resistant=True,
        roles=(CryptoRole.DIGITAL_SIGNATURE, CryptoRole.CONSENSUS_AUTH, CryptoRole.NODE_IDENTITY),
        source_urls=(NIST_FIPS_205, NIST_PQC),
        evidence_as_of=date(2026, 9, 15),
        notes=(
            "Protocol suitability, message size, latency, and operational key handling remain environment-specific.",
        ),
    ),
    "FN-DSA": AlgorithmPolicy(
        algorithm_id="FN-DSA",
        display_name="Falcon-derived FN-DSA",
        standardization_state=StandardizationState.FIPS_IN_DEVELOPMENT,
        standard_reference="FIPS 206 (in development)",
        pq_resistant=True,
        roles=(CryptoRole.DIGITAL_SIGNATURE, CryptoRole.CONSENSUS_AUTH, CryptoRole.NODE_IDENTITY),
        source_urls=(NIST_PQC_STANDARDIZATION,),
        evidence_as_of=date(2026, 9, 15),
        notes=("Not promoted to finalized-FIPS policy state until FIPS 206 is final.",),
    ),
    "HQC": AlgorithmPolicy(
        algorithm_id="HQC",
        display_name="Hamming Quasi-Cyclic KEM",
        standardization_state=StandardizationState.SELECTED_FOR_STANDARDIZATION,
        standard_reference="Selected by NIST; FIPS not final",
        pq_resistant=True,
        roles=(CryptoRole.KEY_ESTABLISHMENT,),
        source_urls=(NIST_HQC, NIST_PQC_STANDARDIZATION),
        evidence_as_of=date(2026, 9, 15),
        notes=("Selected backup KEM is not treated as a finalized production FIPS.",),
    ),
    "HAWK": AlgorithmPolicy(
        algorithm_id="HAWK",
        display_name="HAWK signature candidate",
        standardization_state=StandardizationState.WITHDRAWN,
        standard_reference="Withdrawn from NIST additional-signature process",
        pq_resistant=True,
        roles=(CryptoRole.DIGITAL_SIGNATURE, CryptoRole.CONSENSUS_AUTH, CryptoRole.NODE_IDENTITY),
        source_urls=(NIST_PQC,),
        evidence_as_of=date(2026, 9, 15),
        notes=("Withdrawn candidates are fail-closed for new Worldshepherd deployment policy.",),
    ),
    "ED25519": AlgorithmPolicy(
        algorithm_id="ED25519",
        display_name="Ed25519",
        standardization_state=StandardizationState.CLASSICAL_STANDARD,
        standard_reference="Classical signature algorithm",
        pq_resistant=False,
        roles=(CryptoRole.DIGITAL_SIGNATURE, CryptoRole.CONSENSUS_AUTH, CryptoRole.NODE_IDENTITY),
        source_urls=(),
        evidence_as_of=date(2026, 9, 15),
        notes=("Classical-only algorithm; retained solely for migration/hybrid-state reasoning.",),
    ),
    "ECDSA": AlgorithmPolicy(
        algorithm_id="ECDSA",
        display_name="Elliptic Curve Digital Signature Algorithm",
        standardization_state=StandardizationState.CLASSICAL_STANDARD,
        standard_reference="Classical signature algorithm",
        pq_resistant=False,
        roles=(CryptoRole.DIGITAL_SIGNATURE, CryptoRole.CONSENSUS_AUTH, CryptoRole.NODE_IDENTITY),
        source_urls=(),
        evidence_as_of=date(2026, 9, 15),
        notes=("Classical-only algorithm; retained solely for migration/hybrid-state reasoning.",),
    ),
}


def validate_registry() -> None:
    for key, policy in REGISTRY.items():
        if key != policy.algorithm_id:
            raise ValueError("registry key must equal algorithm_id")
        if not policy.roles:
            raise ValueError(f"{key} must declare at least one cryptographic role")
        if policy.standardization_state is StandardizationState.FINAL_FIPS:
            if not policy.pq_resistant or not policy.standard_reference.startswith("FIPS 20"):
                raise ValueError(f"{key} has inconsistent finalized-PQC metadata")
        if policy.standardization_state is StandardizationState.WITHDRAWN and not policy.notes:
            raise ValueError(f"{key} withdrawal requires an explicit note")


def assess(request: AlgorithmRequest) -> AlgorithmDecision:
    validate_registry()
    policy = REGISTRY.get(request.algorithm_id)
    if policy is None:
        return AlgorithmDecision(
            algorithm_id=request.algorithm_id,
            verdict="BLOCKED_UNKNOWN_ALGORITHM",
            standards_eligible=False,
            deployment_eligible=False,
            pq_posture="UNKNOWN",
            blockers=("Algorithm is not present in the controlled registry.",),
            warnings=(),
            standardization_state="UNKNOWN",
            standard_reference="UNKNOWN",
            role=request.role.value,
            environment=request.environment.value,
            support_tier=request.support_tier.name,
            transition_mode=request.transition_mode.value,
        )

    blockers: list[str] = []
    warnings: list[str] = list(policy.notes)

    age_days = (request.evidence_checked_on - policy.evidence_as_of).days
    if age_days < 0:
        blockers.append("Evidence check date precedes the registry evidence date.")
    elif age_days > request.max_evidence_age_days:
        blockers.append(
            f"Algorithm-policy evidence is stale ({age_days} days > {request.max_evidence_age_days})."
        )

    if request.role not in policy.roles:
        blockers.append(f"Algorithm is not registered for role {request.role.value}.")

    final_fips = policy.standardization_state is StandardizationState.FINAL_FIPS
    standards_eligible = final_fips and policy.pq_resistant and request.role in policy.roles

    if policy.standardization_state is StandardizationState.WITHDRAWN:
        blockers.append("Algorithm was withdrawn from the tracked standardization process.")
    elif policy.standardization_state in {
        StandardizationState.SELECTED_FOR_STANDARDIZATION,
        StandardizationState.FIPS_IN_DEVELOPMENT,
    }:
        blockers.append("Algorithm does not yet have a finalized tracked FIPS in this registry.")
    elif policy.standardization_state is StandardizationState.CLASSICAL_STANDARD:
        blockers.append("Algorithm is classical-only and does not provide PQ resistance.")

    required_support = {
        Environment.LAB: SupportTier.INTERNAL,
        Environment.TESTNET: SupportTier.PUBLIC_TESTNET,
        Environment.PRODUCTION: SupportTier.PRODUCTION,
    }[request.environment]
    if request.support_tier < required_support:
        blockers.append(
            f"{request.environment.value} requires {required_support.name} protocol/client support; "
            f"only {request.support_tier.name} is recorded."
        )

    if request.transition_mode is TransitionMode.CLASSICAL_ONLY and policy.pq_resistant:
        blockers.append("PQ algorithm cannot satisfy a CLASSICAL_ONLY transition request.")
    if request.transition_mode is TransitionMode.PQ_ONLY and not policy.pq_resistant:
        blockers.append("Classical algorithm cannot satisfy a PQ_ONLY transition request.")

    deployment_eligible = standards_eligible and not blockers

    if policy.pq_resistant and request.transition_mode is TransitionMode.HYBRID_TRANSITION:
        pq_posture = "HYBRID_PQ_TRANSITION_COMPONENT"
        warnings.append(
            "Hybrid transition retains a classical dependency; do not label the end-to-end system PQ-only."
        )
    elif policy.pq_resistant and request.transition_mode is TransitionMode.PQ_ONLY:
        pq_posture = "PQ_COMPONENT_CANDIDATE"
    elif not policy.pq_resistant:
        pq_posture = "CLASSICAL_COMPONENT"
    else:
        pq_posture = "UNCLASSIFIED"

    if deployment_eligible:
        verdict = {
            Environment.LAB: "ELIGIBLE_FOR_CONTROLLED_LAB_IMPLEMENTATION",
            Environment.TESTNET: "ELIGIBLE_FOR_PUBLIC_TESTNET_IMPLEMENTATION",
            Environment.PRODUCTION: "ELIGIBLE_FOR_BOUNDED_PRODUCTION_INTEGRATION_REVIEW",
        }[request.environment]
    elif policy.standardization_state is StandardizationState.WITHDRAWN:
        verdict = "BLOCKED_WITHDRAWN"
    elif policy.standardization_state in {
        StandardizationState.SELECTED_FOR_STANDARDIZATION,
        StandardizationState.FIPS_IN_DEVELOPMENT,
    }:
        verdict = "BLOCKED_NOT_FINALIZED"
    elif policy.standardization_state is StandardizationState.CLASSICAL_STANDARD:
        verdict = "BLOCKED_CLASSICAL_ONLY"
    elif request.role not in policy.roles:
        verdict = "BLOCKED_ROLE_MISMATCH"
    elif request.support_tier < required_support:
        verdict = "BLOCKED_DEPLOYMENT_EVIDENCE"
    else:
        verdict = "BLOCKED_POLICY_EVIDENCE"

    return AlgorithmDecision(
        algorithm_id=policy.algorithm_id,
        verdict=verdict,
        standards_eligible=standards_eligible,
        deployment_eligible=deployment_eligible,
        pq_posture=pq_posture,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        standardization_state=policy.standardization_state.value,
        standard_reference=policy.standard_reference,
        role=request.role.value,
        environment=request.environment.value,
        support_tier=request.support_tier.name,
        transition_mode=request.transition_mode.value,
    )


def assert_fail_closed_registry() -> None:
    validate_registry()
    for algorithm_id in ("FN-DSA", "HQC", "HAWK", "ED25519", "ECDSA"):
        request = AlgorithmRequest(
            algorithm_id=algorithm_id,
            role=CryptoRole.KEY_ESTABLISHMENT if algorithm_id == "HQC" else CryptoRole.DIGITAL_SIGNATURE,
            environment=Environment.PRODUCTION,
            support_tier=SupportTier.PRODUCTION,
            transition_mode=TransitionMode.PQ_ONLY if algorithm_id not in {"ED25519", "ECDSA"} else TransitionMode.HYBRID_TRANSITION,
            evidence_checked_on=date(2026, 9, 15),
        )
        if assess(request).deployment_eligible:
            raise AssertionError(f"{algorithm_id} was improperly promoted to deployment eligible")
