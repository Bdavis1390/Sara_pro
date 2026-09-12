"""Claims-controlled readiness classification for archived fusion evidence.

This module prevents analysis-grade archive evidence from being silently
promoted to control-grade evidence.  It evaluates an evidence record's own
quality/uncertainty/control flags; it does not infer missing uncertainty or
machine qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class ArchiveReadinessDecision:
    analysis_eligible: bool
    control_evidence_eligible: bool
    reasons: Tuple[str, ...]


def evaluate_archive_evidence(evidence: Mapping[str, Any]) -> ArchiveReadinessDecision:
    reasons: list[str] = []

    readiness = evidence.get("readiness")
    if not isinstance(readiness, Mapping):
        return ArchiveReadinessDecision(False, False, ("readiness_section_missing",))

    archive_reachable = readiness.get("archive_reachability_confirmed") is True
    integrity_hashed = readiness.get("chunk_integrity_hashed") is True
    decoded_shape = readiness.get("decoded_shape_confirmed") is True
    all_finite = readiness.get("all_values_finite") is True
    time_increasing = readiness.get("time_strictly_increasing") is True
    upstream_quality = str(readiness.get("upstream_quality", "")).strip()
    uncertainty_available = readiness.get("uncertainty_metadata_available") is True

    if not archive_reachable:
        reasons.append("archive_reachability_not_confirmed")
    if not integrity_hashed:
        reasons.append("chunk_integrity_not_hashed")
    if not decoded_shape:
        reasons.append("decoded_shape_not_confirmed")
    if not all_finite:
        reasons.append("nonfinite_values_present_or_unverified")
    if not time_increasing:
        reasons.append("time_base_not_strictly_increasing")

    analysis_eligible = not reasons

    control_reasons = list(reasons)
    if not uncertainty_available:
        control_reasons.append("uncertainty_metadata_unavailable")
    if not upstream_quality or upstream_quality.lower() in {"not checked", "unchecked", "unknown"}:
        control_reasons.append("upstream_quality_not_control_qualified")

    claims = evidence.get("claims_boundary")
    if not isinstance(claims, Mapping):
        control_reasons.append("claims_boundary_missing")
    else:
        if claims.get("real_plasma_state_estimation_validated") is not True:
            control_reasons.append("real_plasma_state_estimation_not_validated")
        if claims.get("real_machine_control_validated") is not True:
            control_reasons.append("real_machine_control_not_validated")

    declared_control = readiness.get("control_evidence_eligible") is True
    if not declared_control:
        control_reasons.append("source_record_declares_control_ineligible")

    # Deduplicate without losing deterministic order.
    deduped_control = tuple(dict.fromkeys(control_reasons))
    return ArchiveReadinessDecision(
        analysis_eligible=analysis_eligible,
        control_evidence_eligible=(analysis_eligible and not deduped_control),
        reasons=deduped_control if deduped_control else tuple(reasons),
    )
