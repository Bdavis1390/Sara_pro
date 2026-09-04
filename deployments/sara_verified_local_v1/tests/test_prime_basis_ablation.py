from __future__ import annotations

from worldshepherd_sara.prime_basis_ablation import (
    AblationOutcome,
    BasisKind,
    default_scenarios,
    is_prime,
    run_prime_basis_ablation,
    verify_prime_basis_ablation_report,
)
from worldshepherd_sara.qualification import CapabilityStatus


def _scenario(report, scenario_id: str):
    return next(item for item in report.scenarios if item.scenario_id == scenario_id)


def _by_basis(scenario):
    return {item.basis: item for item in scenario.results}


def test_prime_predicate_rejects_one_and_forty_nine():
    assert is_prime(1) is False
    assert is_prime(2) is True
    assert is_prime(3) is True
    assert is_prime(49) is False
    assert is_prime(97) is True


def test_default_scenarios_include_positive_negative_and_neutral_controls():
    scenario_ids = {item.scenario_id for item in default_scenarios()}
    assert scenario_ids == {
        "smooth_low_frequency",
        "prime_sparse",
        "composite_sparse",
        "mixed_structure",
        "broadband_decay",
    }


def test_all_basis_rules_receive_equal_rank_and_projection_budget():
    report = run_prime_basis_ablation(sample_count=64, rank=5)
    for scenario in report.scenarios:
        ranks = {item.rank for item in scenario.results}
        terms = {item.basis_terms for item in scenario.results}
        operations = {item.projection_sample_operations for item in scenario.results}
        assert ranks == {5}
        assert terms == {10}
        assert operations == {640}


def test_selected_indices_are_distinct_and_match_declared_rules():
    report = run_prime_basis_ablation(sample_count=64, rank=5)
    first = report.scenarios[0]
    by_basis = _by_basis(first)
    assert by_basis[BasisKind.PRIME].selected_indices == (2, 3, 5, 7, 11)
    assert by_basis[BasisKind.CONTIGUOUS].selected_indices == (1, 2, 3, 4, 5)
    assert by_basis[BasisKind.COMPOSITE].selected_indices == (4, 6, 8, 9, 10)


def test_positive_control_is_won_by_prime_basis():
    report = run_prime_basis_ablation(sample_count=64, rank=5)
    scenario = _scenario(report, "prime_sparse")
    assert scenario.winner == BasisKind.PRIME
    by_basis = _by_basis(scenario)
    assert by_basis[BasisKind.PRIME].relative_l2_error < 1e-10
    assert by_basis[BasisKind.PRIME].relative_l2_error < by_basis[BasisKind.CONTIGUOUS].relative_l2_error
    assert by_basis[BasisKind.PRIME].relative_l2_error < by_basis[BasisKind.COMPOSITE].relative_l2_error


def test_negative_control_is_won_by_composite_basis():
    report = run_prime_basis_ablation(sample_count=64, rank=5)
    scenario = _scenario(report, "composite_sparse")
    assert scenario.winner == BasisKind.COMPOSITE
    by_basis = _by_basis(scenario)
    assert by_basis[BasisKind.COMPOSITE].relative_l2_error < 1e-10
    assert by_basis[BasisKind.COMPOSITE].relative_l2_error < by_basis[BasisKind.PRIME].relative_l2_error


def test_low_frequency_control_is_won_by_contiguous_basis():
    report = run_prime_basis_ablation(sample_count=64, rank=5)
    scenario = _scenario(report, "smooth_low_frequency")
    assert scenario.winner == BasisKind.CONTIGUOUS
    by_basis = _by_basis(scenario)
    assert by_basis[BasisKind.CONTIGUOUS].relative_l2_error < 1e-10
    assert by_basis[BasisKind.CONTIGUOUS].relative_l2_error < by_basis[BasisKind.PRIME].relative_l2_error


def test_default_ablation_does_not_claim_general_prime_advantage():
    report = run_prime_basis_ablation(sample_count=64, rank=5)
    assert report.summary.prime_dominates_every_scenario is False
    assert report.summary.outcome == AblationOutcome.NO_GENERAL_PRIME_ADVANTAGE_OBSERVED
    assert report.preferred_basis_for_general_use is None
    assert report.capability_status == CapabilityStatus.SIMULATED_ONLY
    assert report.physical_validation_performed is False
    assert report.quantum_physics_claimed is False


def test_basis_vectors_remain_numerically_orthogonal_on_test_grid():
    report = run_prime_basis_ablation(sample_count=64, rank=5)
    for scenario in report.scenarios:
        for result in scenario.results:
            assert result.max_normalized_cross_correlation < 1e-12
            assert abs(result.gram_diagonal_ratio - 1.0) < 1e-12


def test_report_is_deterministic_hash_bound_and_tamper_detectable():
    first = run_prime_basis_ablation(sample_count=64, rank=5)
    second = run_prime_basis_ablation(sample_count=64, rank=5)
    assert first == second
    assert first.report_digest is not None
    assert first.report_digest.startswith("sha256:")
    assert verify_prime_basis_ablation_report(first) is True

    tampered = first.model_copy(update={"rank": 4})
    assert verify_prime_basis_ablation_report(tampered) is False


def test_invalid_sampling_or_rank_fails_closed():
    import pytest

    with pytest.raises(ValueError):
        run_prime_basis_ablation(sample_count=63, rank=5)
    with pytest.raises(ValueError):
        run_prime_basis_ablation(sample_count=16, rank=5)
    with pytest.raises(ValueError):
        run_prime_basis_ablation(sample_count=64, rank=0)
