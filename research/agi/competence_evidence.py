from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class EvidenceIndependence(str, Enum):
    PROVIDER_INTERNAL = "PROVIDER_INTERNAL"
    THIRD_PARTY_REPLICATION = "THIRD_PARTY_REPLICATION"
    INDEPENDENT_BLIND = "INDEPENDENT_BLIND"

@dataclass(frozen=True)
class BenchmarkEvidence:
    evidence_id: str
    benchmark: str
    benchmark_version: str
    task_family: str
    domain: str
    candidate_system: str
    harness: str
    score: float
    human_percentile: float | None
    human_reference_population: str | None
    independence: EvidenceIndependence
    interactive: bool
    long_horizon: bool
    real_tool_use: bool
    contamination_risk: str
    source_ref: str

    def validate(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("score must be in [0,1]")
        if self.human_percentile is not None and not 0 <= self.human_percentile <= 100:
            raise ValueError("human percentile must be in [0,100]")
        if self.contamination_risk not in {"LOW","MEDIUM","HIGH","UNKNOWN"}:
            raise ValueError("invalid contamination risk")
        if not self.source_ref:
            raise ValueError("source_ref required")

@dataclass(frozen=True)
class GeneralityEvidencePolicy:
    minimum_percentile: float = 50.0
    minimum_independent_sources_per_family: int = 1
    require_independent_blind: bool = True
    allowed_contamination_risk: tuple[str, ...] = ("LOW", "MEDIUM")

    def validate(self) -> None:
        if not 0 <= self.minimum_percentile <= 100:
            raise ValueError("minimum_percentile must be in [0,100]")
        if self.minimum_independent_sources_per_family < 1:
            raise ValueError("minimum_independent_sources_per_family must be >= 1")

@dataclass
class CompetenceLedger:
    records: list[BenchmarkEvidence] = field(default_factory=list)

    def add(self, evidence: BenchmarkEvidence) -> None:
        evidence.validate()
        self.records.append(evidence)

    def qualifying_family_evidence(
        self,
        candidate_system: str,
        task_family: str,
        policy: GeneralityEvidencePolicy | None = None,
    ) -> list[BenchmarkEvidence]:
        policy = policy or GeneralityEvidencePolicy()
        policy.validate()
        rows = [
            r for r in self.records
            if r.candidate_system == candidate_system
            and r.task_family == task_family
            and r.human_percentile is not None
            and r.human_percentile >= policy.minimum_percentile
            and r.independence in {
                EvidenceIndependence.THIRD_PARTY_REPLICATION,
                EvidenceIndependence.INDEPENDENT_BLIND,
            }
            and r.contamination_risk in policy.allowed_contamination_risk
        ]
        # Multiple rows from the same source/benchmark/harness are not independent
        # replications and must not inflate evidence breadth.
        dedup: dict[tuple[str, str, str], BenchmarkEvidence] = {}
        for row in rows:
            dedup[(row.source_ref, row.benchmark, row.harness)] = row
        return list(dedup.values())

    def family_passes_generality_policy(
        self,
        candidate_system: str,
        task_family: str,
        policy: GeneralityEvidencePolicy | None = None,
    ) -> bool:
        policy = policy or GeneralityEvidencePolicy()
        rows = self.qualifying_family_evidence(candidate_system, task_family, policy)
        if len(rows) < policy.minimum_independent_sources_per_family:
            return False
        if policy.require_independent_blind and not any(
            r.independence == EvidenceIndependence.INDEPENDENT_BLIND for r in rows
        ):
            return False
        return True

    def independently_human_referenced_families(
        self,
        candidate_system: str,
        minimum_percentile: float = 50.0,
    ) -> set[str]:
        policy = GeneralityEvidencePolicy(minimum_percentile=minimum_percentile)
        families = {r.task_family for r in self.records if r.candidate_system == candidate_system}
        return {
            family for family in families
            if self.family_passes_generality_policy(candidate_system, family, policy)
        }

    def family_coverage(
        self,
        candidate_system: str,
        preregistered_families: set[str],
        minimum_percentile: float = 50.0,
        policy: GeneralityEvidencePolicy | None = None,
    ) -> float:
        if not preregistered_families:
            raise ValueError("preregistered families required")
        policy = policy or GeneralityEvidencePolicy(minimum_percentile=minimum_percentile)
        passed = {
            family for family in preregistered_families
            if self.family_passes_generality_policy(candidate_system, family, policy)
        }
        return len(passed) / len(preregistered_families)

    def external_gate_summary(
        self,
        candidate_system: str,
    ) -> dict[str, bool]:
        rows = [r for r in self.records if r.candidate_system == candidate_system]
        externally_usable = [
            r for r in rows
            if r.independence != EvidenceIndependence.PROVIDER_INTERNAL
            and r.contamination_risk != "HIGH"
        ]
        return {
            "novel_interactive_learning": any(r.interactive for r in externally_usable),
            "long_horizon": any(r.long_horizon for r in externally_usable),
            "real_computer_tool_use": any(r.real_tool_use for r in externally_usable),
        }
