from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field, model_validator


SCHEMA_VERSION = "ws-assurance-composite-run-0.1"
SUBSCORE_MAX = {
    "functional_capability": 3,
    "evidence_strength": 3,
    "interoperability": 2,
    "external_use": 2,
}


class DimensionScore(BaseModel):
    functional_capability: int | None = Field(default=None, ge=0, le=3)
    evidence_strength: int | None = Field(default=None, ge=0, le=3)
    interoperability: int | None = Field(default=None, ge=0, le=2)
    external_use: int | None = Field(default=None, ge=0, le=2)
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_score_dependencies(self) -> "DimensionScore":
        values = [
            self.functional_capability,
            self.evidence_strength,
            self.interoperability,
            self.external_use,
        ]
        populated = sum(value is not None for value in values)
        if populated not in (0, 4):
            raise ValueError(
                "a dimension must be fully scored or fully NOT_EVALUATED; "
                "partial scoring is not allowed"
            )
        if populated == 0:
            if self.evidence_refs:
                raise ValueError("NOT_EVALUATED dimensions must not carry evidence_refs")
            return self

        if not self.evidence_refs:
            raise ValueError("a scored dimension requires at least one evidence_ref")

        assert self.functional_capability is not None
        assert self.evidence_strength is not None
        assert self.interoperability is not None
        assert self.external_use is not None

        functional = self.functional_capability
        evidence = self.evidence_strength
        interoperability = self.interoperability
        external = self.external_use

        # Prevent additive-score gaming. Evidence, interoperability and external-use
        # credit depend on a real capability being present at an appropriate level.
        if functional == 0 and any((evidence, interoperability, external)):
            raise ValueError(
                "absent capability (functional_capability=0) cannot receive evidence, "
                "interoperability, or external-use credit"
            )
        if functional == 1:
            if evidence > 1:
                raise ValueError(
                    "documented/design-only capability cannot receive reproducible or "
                    "independent evidence credit"
                )
            if interoperability > 1:
                raise ValueError(
                    "documented/design-only capability cannot receive executable/native "
                    "interoperability credit"
                )
            if external > 0:
                raise ValueError(
                    "documented/design-only capability cannot receive external-use credit"
                )
        if interoperability > 0 and functional < 1:
            raise ValueError("interoperability credit requires a documented capability")
        if interoperability == 2 and functional < 2:
            raise ValueError(
                "native/executable interoperability credit requires implemented capability"
            )
        if evidence >= 2 and functional < 2:
            raise ValueError(
                "reproducible/independent evidence credit requires implemented capability"
            )
        if external > 0 and (functional < 2 or evidence < 1):
            raise ValueError(
                "external-use credit requires implemented capability and attributable evidence"
            )
        if external == 2 and evidence < 2:
            raise ValueError(
                "accepted/upstream/customer-use credit requires reproducible evidence strength"
            )
        return self

    @property
    def evaluated(self) -> bool:
        return self.functional_capability is not None

    @property
    def total(self) -> int | None:
        if not self.evaluated:
            return None
        return int(
            self.functional_capability
            + self.evidence_strength
            + self.interoperability
            + self.external_use
        )


class CandidateScore(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=200)
    artifact_digest: str | None = None
    dimensions: dict[str, DimensionScore]


class BenchmarkRun(BaseModel):
    schema_version: str = SCHEMA_VERSION
    benchmark_version: str = Field(min_length=1, max_length=80)
    benchmark_protocol_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    declared_dimensions: list[str] = Field(min_length=1)
    candidates: list[CandidateScore] = Field(min_length=2)
    comparison_set_rationale: str | None = Field(default=None, max_length=8000)
    external_evaluator_record: str | None = None
    raw_results_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def validate_dimensions_and_candidates(self) -> "BenchmarkRun":
        if len(set(self.declared_dimensions)) != len(self.declared_dimensions):
            raise ValueError("declared_dimensions must be unique")
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(set(ids)) != len(ids):
            raise ValueError("candidate_id values must be unique")
        allowed = set(self.declared_dimensions)
        for candidate in self.candidates:
            extra = set(candidate.dimensions) - allowed
            if extra:
                raise ValueError(
                    f"candidate {candidate.candidate_id!r} contains undeclared dimensions: "
                    f"{sorted(extra)}"
                )
        return self


def _score_for(candidate: CandidateScore, dimension: str) -> DimensionScore:
    return candidate.dimensions.get(dimension, DimensionScore())


def evaluate_run(run: BenchmarkRun) -> dict[str, Any]:
    common_dimensions: list[str] = []
    not_evaluated: dict[str, list[str]] = {}

    for dimension in run.declared_dimensions:
        missing = [
            candidate.candidate_id
            for candidate in run.candidates
            if not _score_for(candidate, dimension).evaluated
        ]
        if missing:
            not_evaluated[dimension] = missing
        else:
            common_dimensions.append(dimension)

    candidate_results: list[dict[str, Any]] = []
    for candidate in run.candidates:
        total = sum(
            _score_for(candidate, dimension).total or 0
            for dimension in common_dimensions
        )
        maximum = len(common_dimensions) * 10
        candidate_results.append(
            {
                "candidate_id": candidate.candidate_id,
                "version": candidate.version,
                "artifact_digest": candidate.artifact_digest,
                "comparable_total": total,
                "comparable_max": maximum,
                "comparable_percent": (
                    round((total / maximum) * 100, 6) if maximum else None
                ),
            }
        )

    full_comparison = len(common_dimensions) == len(run.declared_dimensions)
    ordered = sorted(
        candidate_results,
        key=lambda item: item["comparable_total"],
        reverse=True,
    )
    winner: str | None = None
    if full_comparison and len(ordered) >= 2:
        if ordered[0]["comparable_total"] > ordered[1]["comparable_total"]:
            winner = str(ordered[0]["candidate_id"])

    all_candidates_frozen = all(
        bool(candidate.artifact_digest) for candidate in run.candidates
    )
    claim_ready = bool(
        full_comparison
        and winner
        and all_candidates_frozen
        and run.benchmark_protocol_sha256
        and run.comparison_set_rationale
        and run.external_evaluator_record
        and run.raw_results_sha256
    )

    return {
        "schema_version": run.schema_version,
        "benchmark_version": run.benchmark_version,
        "benchmark_protocol_sha256": run.benchmark_protocol_sha256,
        "declared_dimensions": run.declared_dimensions,
        "common_comparable_dimensions": common_dimensions,
        "not_evaluated": not_evaluated,
        "full_comparison": full_comparison,
        "all_candidates_frozen": all_candidates_frozen,
        "candidate_results": candidate_results,
        "winner": winner,
        "claim_ready": claim_ready,
        "claim_boundary": (
            "A winner is benchmark-scoped only. Universal superiority is not established."
        ),
    }


def canonical_payload(result: dict[str, Any]) -> bytes:
    return json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def result_digest(result: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(result)).hexdigest()
