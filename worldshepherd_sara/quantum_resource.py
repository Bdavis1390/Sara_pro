"""Governance contract for fault-tolerant quantum resource estimates.

This module validates estimates produced by external estimators. It does not
calculate physical resources itself and therefore cannot be used to claim
fault-tolerant feasibility without an estimator-backed record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ResourceEstimateRecord:
    benchmark_id: str
    estimator_name: str
    estimator_version: str
    program_digest: str
    logical_qubits: int
    logical_gate_count: int
    target_logical_error_rate: float
    error_correction_model: str
    physical_qubits_estimate: int
    estimated_runtime_seconds: float
    non_clifford_count: int | None = None
    code_distance: int | None = None
    assumptions: Mapping[str, str] | None = None


@dataclass(frozen=True)
class ResourceEstimateDecision:
    accepted: bool
    reasons: tuple[str, ...]


def validate_resource_estimate(record: ResourceEstimateRecord) -> ResourceEstimateDecision:
    reasons: list[str] = []

    if not record.benchmark_id.strip():
        reasons.append("benchmark_id is required")
    if not record.estimator_name.strip() or not record.estimator_version.strip():
        reasons.append("estimator name and version are required")
    if not record.program_digest.startswith("sha256:"):
        reasons.append("program_digest must be a sha256 identity")
    if record.logical_qubits <= 0:
        reasons.append("logical_qubits must be positive")
    if record.logical_gate_count <= 0:
        reasons.append("logical_gate_count must be positive")
    if not 0 < record.target_logical_error_rate < 1:
        reasons.append("target_logical_error_rate must be in (0, 1)")
    if not record.error_correction_model.strip():
        reasons.append("error_correction_model is required")
    if record.physical_qubits_estimate < record.logical_qubits:
        reasons.append("physical_qubits_estimate cannot be below logical_qubits")
    if record.estimated_runtime_seconds <= 0:
        reasons.append("estimated_runtime_seconds must be positive")
    if record.non_clifford_count is not None and record.non_clifford_count < 0:
        reasons.append("non_clifford_count cannot be negative")
    if record.code_distance is not None and record.code_distance <= 0:
        reasons.append("code_distance must be positive when provided")
    if not record.assumptions:
        reasons.append("estimator assumptions must be retained")

    return ResourceEstimateDecision(accepted=not reasons, reasons=tuple(reasons))
