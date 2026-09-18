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

@dataclass
class CompetenceLedger:
    records: list[BenchmarkEvidence] = field(default_factory=list)

    def add(self, evidence: BenchmarkEvidence) -> None:
        evidence.validate()
        self.records.append(evidence)

    def independently_human_referenced_families(
        self,
        candidate_system: str,
        minimum_percentile: float = 50.0,
    ) -> set[str]:
        return {
            r.task_family
            for r in self.records
            if r.candidate_system == candidate_system
            and r.human_percentile is not None
            and r.human_percentile >= minimum_percentile
            and r.independence in {
                EvidenceIndependence.THIRD_PARTY_REPLICATION,
                EvidenceIndependence.INDEPENDENT_BLIND,
            }
            and r.contamination_risk != "HIGH"
        }

    def family_coverage(
        self,
        candidate_system: str,
        preregistered_families: set[str],
        minimum_percentile: float = 50.0,
    ) -> float:
        if not preregistered_families:
            raise ValueError("preregistered families required")
        passed = self.independently_human_referenced_families(
            candidate_system, minimum_percentile
        ) & preregistered_families
        return len(passed) / len(preregistered_families)

    def external_gate_summary(
        self,
        candidate_system: str,
    ) -> dict[str, bool]:
        rows = [r for r in self.records if r.candidate_system == candidate_system]
        return {
            "novel_interactive_learning": any(
                r.interactive
                and r.independence != EvidenceIndependence.PROVIDER_INTERNAL
                for r in rows
            ),
            "long_horizon": any(
                r.long_horizon
                and r.independence != EvidenceIndependence.PROVIDER_INTERNAL
                for r in rows
            ),
            "real_computer_tool_use": any(
                r.real_tool_use
                and r.independence != EvidenceIndependence.PROVIDER_INTERNAL
                for r in rows
            ),
        }
