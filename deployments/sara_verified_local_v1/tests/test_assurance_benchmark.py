import pytest
from pydantic import ValidationError

from worldshepherd_sara.assurance_benchmark import (
    BenchmarkRun,
    CandidateScore,
    DimensionScore,
    evaluate_run,
)


def _score(total: int, ref: str = "evidence://fixture") -> DimensionScore:
    # Encode totals 0..10 using the benchmark's 3/3/2/2 maxima.
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


def test_unknown_is_not_zero_and_blocks_full_comparison() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        declared_dimensions=["A1", "A2"],
        candidates=[
            CandidateScore(
                candidate_id="worldshepherd",
                version="sha-1",
                dimensions={"A1": _score(9), "A2": _score(8)},
            ),
            CandidateScore(
                candidate_id="competitor",
                version="v1",
                dimensions={"A1": _score(7)},
            ),
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


def test_full_comparison_with_external_record_can_be_claim_ready() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        declared_dimensions=["A1", "A2"],
        external_evaluator_record="evaluator://independent/record-1",
        raw_results_sha256="a" * 64,
        candidates=[
            CandidateScore(
                candidate_id="worldshepherd",
                version="sha-1",
                dimensions={"A1": _score(10), "A2": _score(9)},
            ),
            CandidateScore(
                candidate_id="competitor",
                version="v1",
                dimensions={"A1": _score(8), "A2": _score(8)},
            ),
        ],
    )
    result = evaluate_run(run)
    assert result["full_comparison"] is True
    assert result["winner"] == "worldshepherd"
    assert result["claim_ready"] is True


def test_internal_only_comparison_cannot_be_claim_ready() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        declared_dimensions=["A1"],
        candidates=[
            CandidateScore(
                candidate_id="worldshepherd",
                version="sha-1",
                dimensions={"A1": _score(10)},
            ),
            CandidateScore(
                candidate_id="competitor",
                version="v1",
                dimensions={"A1": _score(9)},
            ),
        ],
    )
    result = evaluate_run(run)
    assert result["winner"] == "worldshepherd"
    assert result["claim_ready"] is False


def test_tie_has_no_winner() -> None:
    run = BenchmarkRun(
        benchmark_version="0.1",
        declared_dimensions=["A1"],
        external_evaluator_record="evaluator://record",
        raw_results_sha256="b" * 64,
        candidates=[
            CandidateScore(
                candidate_id="worldshepherd",
                version="sha-1",
                dimensions={"A1": _score(9)},
            ),
            CandidateScore(
                candidate_id="competitor",
                version="v1",
                dimensions={"A1": _score(9)},
            ),
        ],
    )
    result = evaluate_run(run)
    assert result["winner"] is None
    assert result["claim_ready"] is False
