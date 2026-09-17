"""Two-key transition gate for post-quantum proof-of-stake readiness.

This module composes the standards-aware algorithm lifecycle policy with the
existing seven-axis PoS readiness classifier. Neither plane can self-promote the
other:

* a finalized PQ algorithm does not make a protocol PQ-ready; and
* protocol/testnet PQ evidence does not make a non-final, withdrawn, stale, or
  unsupported algorithm eligible.

The gate is claims-control software only. It does not implement cryptography,
modify consensus, submit transactions, rotate keys, or authorize live value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from security.qcrypto.pos_pq_readiness import (
    EvidenceTier,
    ReadinessAssessment,
    ReadinessEvidence,
    assess as assess_readiness,
)
from security.qcrypto.pqc_algorithm_policy import (
    AlgorithmDecision,
    AlgorithmRequest,
    Environment,
    TransitionMode,
    assess as assess_algorithm,
)


@dataclass(frozen=True)
class PosPqcTransitionAssessment:
    profile_id: str
    algorithm_id: str
    environment: str
    verdict: str
    algorithm_verdict: str
    system_classification: str
    algorithm_policy_pass: bool
    system_evidence_pass: bool
    transition_candidate: bool
    production_integration_review_eligible: bool
    production_pq_consensus_ready: bool
    end_to_end_pq_security_established: bool
    hybrid_dependency_present: bool
    blocking_system_axes: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    claim_boundary: str = (
        "Cross-layer PQ transition classification only; this does not establish "
        "production PQ consensus readiness, end-to-end post-quantum security, "
        "FIPS module validation, protocol conformance, Federal compliance, live-value "
        "authorization, or deployment authority."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blocking_system_axes"] = list(self.blocking_system_axes)
        data["blockers"] = list(self.blockers)
        data["warnings"] = list(self.warnings)
        return data


def _system_threshold(
    readiness: ReadinessAssessment,
    record: ReadinessEvidence,
    environment: Environment,
) -> tuple[bool, tuple[str, ...]]:
    values = record.evidence_map()

    if environment is Environment.LAB:
        required = EvidenceTier.INTERNAL_INTEROP
        required_axes = (
            "consensus_signature_acceptance",
            "protocol_client_support",
        )
    elif environment is Environment.TESTNET:
        required = EvidenceTier.PUBLIC_TESTNET
        required_axes = (
            "consensus_signature_acceptance",
            "protocol_client_support",
        )
    else:
        # Production integration review requires the existing readiness model's
        # strongest state: every system axis at PRODUCTION evidence grade.
        return readiness.production_ready, readiness.blocking_axes

    blocking = tuple(axis for axis in required_axes if values[axis] < required)
    return not blocking, blocking


def assess_transition(
    readiness_record: ReadinessEvidence,
    algorithm_request: AlgorithmRequest,
) -> PosPqcTransitionAssessment:
    readiness = assess_readiness(readiness_record)
    algorithm = assess_algorithm(algorithm_request)
    system_pass, threshold_blockers = _system_threshold(
        readiness,
        readiness_record,
        algorithm_request.environment,
    )

    blockers: list[str] = []
    warnings: list[str] = list(algorithm.warnings)

    algorithm_pass = algorithm.deployment_eligible
    if not algorithm_pass:
        blockers.append(f"Algorithm policy blocked transition: {algorithm.verdict}.")
        blockers.extend(algorithm.blockers)
    if not system_pass:
        blockers.append(
            f"System evidence does not satisfy {algorithm_request.environment.value} transition threshold."
        )
        if threshold_blockers:
            blockers.append(
                "Blocking system axes: " + ", ".join(threshold_blockers) + "."
            )

    hybrid = algorithm_request.transition_mode is TransitionMode.HYBRID_TRANSITION
    if hybrid:
        warnings.append(
            "Hybrid transition retains at least one classical dependency; end-to-end PQ-only status is prohibited."
        )

    transition_candidate = algorithm_pass and system_pass
    production_review = (
        transition_candidate
        and algorithm_request.environment is Environment.PRODUCTION
        and readiness.production_ready
    )

    if not algorithm_pass:
        verdict = "BLOCKED_ALGORITHM_POLICY"
    elif not system_pass:
        verdict = "BLOCKED_SYSTEM_READINESS"
    elif algorithm_request.environment is Environment.LAB:
        verdict = "CONTROLLED_LAB_PQ_INTEROP_CANDIDATE"
    elif algorithm_request.environment is Environment.TESTNET:
        verdict = (
            "PUBLIC_TESTNET_HYBRID_VALIDATOR_AUTH_CANDIDATE"
            if hybrid
            else "PUBLIC_TESTNET_PQ_VALIDATOR_AUTH_CANDIDATE"
        )
    else:
        verdict = "BOUNDED_PRODUCTION_PQ_CONSENSUS_INTEGRATION_REVIEW"

    # This gate intentionally never self-asserts production PQ consensus or
    # end-to-end PQ security. Those require separate deployment/independent
    # evidence beyond algorithm + internal readiness classification.
    return PosPqcTransitionAssessment(
        profile_id=readiness_record.profile_id,
        algorithm_id=algorithm_request.algorithm_id,
        environment=algorithm_request.environment.value,
        verdict=verdict,
        algorithm_verdict=algorithm.verdict,
        system_classification=readiness.classification,
        algorithm_policy_pass=algorithm_pass,
        system_evidence_pass=system_pass,
        transition_candidate=transition_candidate,
        production_integration_review_eligible=production_review,
        production_pq_consensus_ready=False,
        end_to_end_pq_security_established=False,
        hybrid_dependency_present=hybrid,
        blocking_system_axes=threshold_blockers,
        blockers=tuple(blockers),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def assert_real_world_fail_closed(
    records: dict[str, ReadinessEvidence],
    requests: dict[str, AlgorithmRequest],
) -> None:
    """Assert no supplied real-world record self-promotes to production-ready."""
    if set(records) != set(requests):
        raise AssertionError("records and algorithm requests must cover the same profile IDs")
    for profile_id, record in records.items():
        result = assess_transition(record, requests[profile_id])
        if result.production_pq_consensus_ready:
            raise AssertionError(f"{profile_id} was improperly promoted to production PQ consensus")
        if result.end_to_end_pq_security_established:
            raise AssertionError(f"{profile_id} was improperly promoted to end-to-end PQ security")
