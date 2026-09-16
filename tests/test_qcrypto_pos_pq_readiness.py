from __future__ import annotations

from dataclasses import replace

import pytest

from security.qcrypto.pos_family_preservation import PROFILES
from security.qcrypto.pos_pq_benchmarks import BENCHMARKS
from security.qcrypto.pos_pq_readiness import (
    AXES,
    BENCHMARK_EVIDENCE,
    TARGET_EVIDENCE,
    EvidenceTier,
    ReadinessEvidence,
    assess,
    assess_all_benchmarks,
    assess_all_targets,
    assert_fail_closed_claims,
)


def test_every_target_and_benchmark_has_explicit_record() -> None:
    assert set(TARGET_EVIDENCE) == set(PROFILES)
    assert set(BENCHMARK_EVIDENCE) == set(BENCHMARKS)


def test_no_reviewed_production_target_is_promoted_to_pq_consensus_ready() -> None:
    results = assess_all_targets()
    assert all(not result.production_ready for result in results.values())
    assert all(result.classification != "PRODUCTION_PQ_CONSENSUS_READY" for result in results.values())
    assert_fail_closed_claims()


def test_algorand_pq_accounts_do_not_promote_consensus() -> None:
    result = assess_all_targets()["ALGORAND"]
    evidence = dict(result.evidence)
    assert evidence["economic_owner_or_governance_auth"] == "PRODUCTION"
    assert evidence["consensus_signature_acceptance"] != "PRODUCTION"
    assert result.classification == "PRODUCTION_PQ_COMPONENT_ONLY"
    assert result.production_ready is False
    assert "consensus_signature_acceptance" in result.blocking_axes


def test_ethereum_roadmap_stays_development_grade() -> None:
    result = assess_all_targets()["ETHEREUM"]
    assert result.classification == "PQ_TRANSITION_IN_EXTERNAL_DEVELOPMENT"
    assert result.production_ready is False
    assert dict(result.evidence)["protocol_client_support"] == "EXTERNAL_DESIGN"


def test_qrl_external_benchmark_stops_at_public_testnet() -> None:
    result = assess_all_benchmarks()["QRL2_TESTNET"]
    assert result.classification == "PUBLIC_PQ_VALIDATOR_AUTH_TESTNET"
    assert result.production_ready is False
    evidence = dict(result.evidence)
    assert evidence["consensus_signature_acceptance"] == "PUBLIC_TESTNET"
    assert evidence["protocol_client_support"] == "PUBLIC_TESTNET"
    assert "aggregation_or_finality" in result.blocking_axes


def test_internal_signature_interop_alone_cannot_promote_production() -> None:
    result = assess_all_targets()["SOLANA"]
    assert result.classification == "INTERNAL_PQ_INTEROP_ONLY"
    assert result.production_ready is False
    assert dict(result.evidence)["consensus_signature_acceptance"] == "INTERNAL_INTEROP"


def test_production_ready_requires_every_axis_at_production_grade() -> None:
    record = ReadinessEvidence(
        profile_id="SYNTHETIC",
        evidence=tuple((axis, EvidenceTier.PRODUCTION) for axis in AXES),
        external_state="SYNTHETIC_TEST_ONLY",
    )
    result = assess(record)
    assert result.production_ready is True
    assert result.classification == "PRODUCTION_PQ_CONSENSUS_READY"
    assert result.blocking_axes == ()


def test_one_missing_axis_forces_fail_closed_result() -> None:
    evidence = [(axis, EvidenceTier.PRODUCTION) for axis in AXES]
    evidence[AXES.index("operational_key_lifecycle")] = (
        "operational_key_lifecycle",
        EvidenceTier.PUBLIC_TESTNET,
    )
    result = assess(
        ReadinessEvidence(
            profile_id="SYNTHETIC",
            evidence=tuple(evidence),
            external_state="SYNTHETIC_TEST_ONLY",
        )
    )
    assert result.production_ready is False
    assert "operational_key_lifecycle" in result.blocking_axes


def test_missing_or_reordered_axes_fail_validation() -> None:
    with pytest.raises(ValueError):
        assess(
            ReadinessEvidence(
                profile_id="BROKEN",
                evidence=((AXES[0], EvidenceTier.PRODUCTION),),
                external_state="BROKEN_TEST_ONLY",
            )
        )

    reversed_record = ReadinessEvidence(
        profile_id="BROKEN",
        evidence=tuple((axis, EvidenceTier.PRODUCTION) for axis in reversed(AXES)),
        external_state="BROKEN_TEST_ONLY",
    )
    with pytest.raises(ValueError):
        assess(reversed_record)
