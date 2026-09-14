"""Explicit admission boundary between archive analysis and control evidence.

Callers must pass a claims-controlled archive evidence record through this gate
before using that archive as control evidence.  This prevents a downstream
caller from upgrading an analysis-only dataset by supplying ad-hoc uncertainty
or confidence values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from worldshepherd_sara.archive_readiness import ArchiveReadinessDecision, evaluate_archive_evidence


@dataclass(frozen=True)
class ControlAdmissionResult:
    admitted: bool
    reason: str
    blockers: Tuple[str, ...]


class ArchiveControlAdmissionGate:
    def evaluate(self, evidence: Mapping[str, Any]) -> ControlAdmissionResult:
        readiness = evaluate_archive_evidence(evidence)
        if not readiness.analysis_eligible:
            return ControlAdmissionResult(
                admitted=False,
                reason="archive_not_analysis_eligible",
                blockers=readiness.reasons,
            )
        if not readiness.control_evidence_eligible:
            return ControlAdmissionResult(
                admitted=False,
                reason="archive_not_control_evidence_eligible",
                blockers=readiness.reasons,
            )
        return ControlAdmissionResult(True, "control_evidence_admitted", ())

    def require(self, evidence: Mapping[str, Any]) -> None:
        decision = self.evaluate(evidence)
        if not decision.admitted:
            joined = ",".join(decision.blockers)
            raise ValueError(f"{decision.reason}:{joined}")
