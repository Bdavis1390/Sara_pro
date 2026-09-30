import pytest
from pydantic import ValidationError

from worldshepherd_sara.assurance_benchmark import (
    BenchmarkRun,
    CandidateScore,
    DimensionScore,
    evaluate_run,
)


def _score(total: int, ref: str = "evidence://fixture") -> DimensionScore:
    # Encode totals 0..10 using the benchmark's 3/3/2/2 maxima while preserving
    # score dependencies (capability before evidence/interoperability/use).
    remaining = total
    functional = min(3, remaining)
    remaining -= functional
    evidence = min(3, remaining)
    remaining -= evidence
    interoperability = min(2, remaining)
    remaining -= interoperability
    external = min(2, remaining)
    return DimensionScore(
        functional_capability=functional,
        evidence_strength=evidence,
        interoperability=interoperability,
        external_use=external,
        evidence_refs=[ref],
    )


def _candidate(candidate_id: str, version: str, dimensions) -> CandidateScore:
    return CandidateScore(
        candidate_id=candidate_id,
        version=version,
        artifact_digest=f"sha256:{candidate_id}-fixture",
        dimensions=dimensions,
    )


def test_unknown_is_not_zero_and_blocks_full_comparison() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        declared_dimensions=["A1", "A2"],
        candidates=[
            _candidate(
                "worldshepherd",
                "sha-1",
                {"A1": _score(9), "A2": _score(8)},
            ),
            _candidate("competitor", "v1", {"A1": _score(7)}),
        ],
    )
    result = evaluate_run(run)
    assert result["common_comparable_dimensions"] == ["A1"]
    assert result["not_evaluated"] == {"A2": ["competitor"]}
    assert result["full_comparison"] is False
    assert result["winner"] is None
    assert result["claim_ready"] is False


def test_partial_dimension_score_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionScore(
            functional_capability=3,
            evidence_strength=2,
            evidence_refs=["evidence://partial"],
        )


def test_scored_dimension_requires_evidence_reference() -> None:
    with pytest.raises(ValidationError):
        DimensionScore(
            functional_capability=3,
            evidence_strength=3,
            interoperability=2,
            external_use=2,
        )


def test_not_evaluated_dimension_cannot_carry_evidence_reference() -> None:
    with pytest.raises(ValidationError, match="NOT_EVALUATED"):
        DimensionScore(evidence_refs=["evidence://should-not-exist"])


def test_absent_capability_cannot_get_other_credit() -> None:
    with pytest.raises(ValidationError, match="absent capability"):
        DimensionScore(
            functional_capability=0,
            evidence_strength=2,
            interoperability=0,
            external_use=0,
            evidence_refs=["evidence://absence"],
        )


def test_design_only_capability_cannot_get_external_use_credit() -> None:
    with pytest.raises(ValidationError, match="design-only"):
        DimensionScore(
            functional_capability=1,
            evidence_strength=1,
            interoperability=1,
            external_use=1,
            evidence_refs=["evidence://design"],
        )


def test_max_external_use_requires_reproducible_evidence() -> None:
    with pytest.raises(ValidationError, match="reproducible evidence"):
        DimensionScore(
            functional_capability=3,
            evidence_strength=1,
            interoperability=2,
            external_use=2,
            evidence_refs=["evidence://external-use"],
        )


def test_full_comparison_with_all_claim_gates_can_be_claim_ready() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        benchmark_protocol_sha256="c" * 64,
        declared_dimensions=["A1", "A2"],
        comparison_set_rationale=(
            "Best-of-breed public comparison set selected before scoring."
        ),
        external_evaluator_record="evaluator://independent/record-1",
        raw_results_sha256="a" * 64,
        candidates=[
            _candidate(
                "worldshepherd",
                "sha-1",
                {"A1": _score(10), "A2": _score(9)},
            ),
            _candidate(
                "competitor",
                "v1",
                {"A1": _score(8), "A2": _score(8)},
            ),
        ],
    )
    result = evaluate_run(run)
    assert result["full_comparison"] is True
    assert result["all_candidates_frozen"] is True
    assert result["winner"] == "worldshepherd"
    assert result["claim_ready"] is True


def test_unfrozen_candidate_blocks_claim_readiness() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        benchmark_protocol_sha256="d" * 64,
        declared_dimensions=["A1"],
        comparison_set_rationale="Predeclared comparison set.",
        external_evaluator_record="evaluator://record",
        raw_results_sha256="e" * 64,
        candidates=[
            CandidateScore(
                candidate_id="worldshepherd",
                version="sha-1",
                artifact_digest="sha256:worldshepherd",
                dimensions={"A1": _score(10)},
            ),
            CandidateScore(
                candidate_id="competitor",
                version="moving-latest",
                dimensions={"A1": _score(9)},
            ),
        ],
    )
    result = evaluate_run(run)
    assert result["winner"] == "worldshepherd"
    assert result["all_candidates_frozen"] is False
    assert result["claim_ready"] is False


def test_internal_only_comparison_cannot_be_claim_ready() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        declared_dimensions=["A1"],
        candidates=[
            _candidate("worldshepherd", "sha-1", {"A1": _score(10)}),
            _candidate("competitor", "v1", {"A1": _score(9)}),
        ],
    )
    result = evaluate_run(run)
    assert result["winner"] == "worldshepherd"
    assert result["claim_ready"] is False


def test_tie_has_no_winner() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        benchmark_protocol_sha256="f" * 64,
        declared_dimensions=["A1"],
        comparison_set_rationale="Predeclared comparison set.",
        external_evaluator_record="evaluator://record",
        raw_results_sha256="b" * 64,
        candidates=[
            _candidate("worldshepherd", "sha-1", {"A1": _score(9)}),
            _candidate("competitor", "v1", {"A1": _score(9)}),
        ],
    )
    result = evaluate_run(run)
    assert result["winner"] is None
    assert result["claim_ready"] is False
