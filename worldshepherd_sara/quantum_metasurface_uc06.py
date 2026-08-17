"""Bridge retained UC06 Palace reconstruction status into QRF without promoting calibration.

This module records source-supported solver progress as a pre-calibration status object.
It deliberately distinguishes transcript/review evidence from raw full-wave artifacts in
QRF custody. The bridge cannot satisfy WS-METASURFACE-EXT-01 by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any


def _digest(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class UC06PrecalibrationSummary:
    campaign_id: str
    solver: str
    source_class: str
    source_refs: tuple[str, ...]
    six_smoke_runtime_matrix_complete: bool
    historical_points_compared: int
    historical_points_total: int
    parameter_tuning_applied: bool
    post_hoc_threshold_applied: bool
    frozen_convergence_gate_passed: bool
    semantic_equivalence_established: bool
    numerical_equivalence_established: bool
    vna_correlation_executed: bool
    full_campaign_authorized: bool
    raw_solver_artifacts_in_qrf_custody: bool


@dataclass(frozen=True)
class UC06PrecalibrationDecision:
    accepted_as_precalibration_status: bool
    calibration_gate_satisfied: bool
    status: str
    blockers: tuple[str, ...]
    summary_digest: str
    next_action: str
    claim_control: str


def evaluate_uc06_precalibration(summary: UC06PrecalibrationSummary) -> UC06PrecalibrationDecision:
    reasons: list[str] = []
    if not summary.campaign_id.strip() or not summary.solver.strip():
        reasons.append("campaign_id and solver are required")
    if not summary.source_refs:
        reasons.append("at least one retained source reference is required")
    if summary.historical_points_total <= 0:
        reasons.append("historical_points_total must be positive")
    if not 0 <= summary.historical_points_compared <= summary.historical_points_total:
        reasons.append("historical_points_compared must be within the declared total")

    accepted = not reasons and summary.six_smoke_runtime_matrix_complete and summary.historical_points_compared == summary.historical_points_total
    blockers: list[str] = []
    if not summary.frozen_convergence_gate_passed:
        blockers.append("frozen convergence gate failed")
    if not summary.semantic_equivalence_established:
        blockers.append("semantic equivalence not established")
    if not summary.numerical_equivalence_established:
        blockers.append("numerical equivalence not established")
    if not summary.vna_correlation_executed:
        blockers.append("VNA correlation not executed")
    if not summary.full_campaign_authorized:
        blockers.append("full campaign not authorized")
    if not summary.raw_solver_artifacts_in_qrf_custody:
        blockers.append("raw solver artifacts are not yet in QRF custody")
    if summary.parameter_tuning_applied:
        blockers.append("parameter tuning was applied to the frozen comparison")
    if summary.post_hoc_threshold_applied:
        blockers.append("post-hoc thresholding was applied")

    calibration_gate = accepted and not blockers
    payload = asdict(summary)
    return UC06PrecalibrationDecision(
        accepted_as_precalibration_status=accepted,
        calibration_gate_satisfied=calibration_gate,
        status=("READY_FOR_RAW_CALIBRATION_INGEST" if calibration_gate else "PRECALIBRATION_EVIDENCE_PRESENT_GATE_NOT_SATISFIED"),
        blockers=tuple(reasons + blockers),
        summary_digest=_digest(payload),
        next_action=(
            "ingest retained raw full-wave artifacts, resolve convergence/model discrepancy, establish numerical and semantic equivalence, "
            "complete protocol-required VNA correlation, and authorize the frozen full campaign before reduced-objective calibration"
        ),
        claim_control=(
            "This decision records retained UC06 pre-calibration status only. It is not a full-wave calibration result, does not place raw solver "
            "artifacts in QRF custody, does not satisfy WS-METASURFACE-EXT-01, and cannot raise mission readiness."
        ),
    )


def retained_uc06_status() -> UC06PrecalibrationDecision:
    summary = UC06PrecalibrationSummary(
        campaign_id="UC06-P1-R1",
        solver="Palace 0.17.0 reconstruction campaign",
        source_class="retained_project_transcript_and_reconstruction_audit_not_raw_solver_artifact",
        source_refs=("UC06-P1 R1-M six-smoke Palace runtime matrix", "UC06-P1 R1-N 18-point reconstruction audit"),
        six_smoke_runtime_matrix_complete=True,
        historical_points_compared=18,
        historical_points_total=18,
        parameter_tuning_applied=False,
        post_hoc_threshold_applied=False,
        frozen_convergence_gate_passed=False,
        semantic_equivalence_established=False,
        numerical_equivalence_established=False,
        vna_correlation_executed=False,
        full_campaign_authorized=False,
        raw_solver_artifacts_in_qrf_custody=False,
    )
    return evaluate_uc06_precalibration(summary)
