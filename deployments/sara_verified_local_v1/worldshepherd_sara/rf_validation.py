from __future__ import annotations

from typing import Any

from .discrepancy import PairedMeasurement, compare_prediction_to_measurement
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_synthetic_rf_discrepancy(
    *,
    fixture: dict[str, Any],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    pairs = [
        PairedMeasurement(
            key=f"s11_{point['frequency_ghz']}ghz",
            predicted=float(point["predicted_s11_db"]),
            measured=float(point["measured_s11_db"]),
            uncertainty=float(point["measurement_uncertainty_db"]),
            units="dB",
        )
        for point in fixture["points"]
    ]
    summary = compare_prediction_to_measurement(pairs)
    expected = fixture["expected"]
    within_fraction = summary.within_uncertainty_fraction
    passed = (
        summary.max_absolute_error <= float(expected["max_absolute_error_db"])
        and within_fraction is not None
        and within_fraction >= float(expected["minimum_within_uncertainty_fraction"])
    )

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-7001",
        requirement_id=requirement.requirement_delta_id,
        test_id="rf_synthetic_discrepancy_v1",
        evidence_scope=EvidenceScope.SIMULATION,
        capability_status=CapabilityStatus.SIMULATED_ONLY,
        environment_digest=canonical_digest(
            {"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}
        ),
        configuration_digest=canonical_digest({"comparison": "paired_s11_db_v1"}),
        inputs=[{"point_count": len(fixture["points"])}],
        outputs=[
            {
                "mean_absolute_error_db": summary.mean_absolute_error,
                "max_absolute_error_db": summary.max_absolute_error,
                "within_uncertainty_fraction": summary.within_uncertainty_fraction,
                "metrics": [
                    {
                        "key": metric.key,
                        "absolute_error": metric.absolute_error,
                        "relative_error": metric.relative_error,
                        "normalized_error": metric.normalized_error,
                        "units": metric.units,
                    }
                    for metric in summary.metrics
                ],
            }
        ],
        metrics=[
            {"name": "max_absolute_error_db", "value": summary.max_absolute_error, "target_max": expected["max_absolute_error_db"]},
            {"name": "within_uncertainty_fraction", "value": summary.within_uncertainty_fraction, "target_min": expected["minimum_within_uncertainty_fraction"]},
        ],
        uncertainty=[
            {"name": "physical_measurement_validity", "state": "NOT_EVALUATED", "note": "fixture measurements are synthetic"},
            {"name": "fabrication_variability", "state": "NOT_EVALUATED"},
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=(
            "Synthetic predicted/measured S11-like values met frozen discrepancy targets"
            if passed
            else "Synthetic predicted/measured S11-like values exceeded one or more frozen discrepancy targets"
        ),
        negative_evidence=[] if passed else [{"max_absolute_error_db": summary.max_absolute_error, "within_uncertainty_fraction": summary.within_uncertainty_fraction}],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
        physical_validation_performed=False,
    )
    bundle = compile_qualification_bundle(requirement, [evidence])
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["scope_note"] = (
        "Synthetic RF simulation-to-measurement discrepancy exercise only; no VNA/chamber/fabricated metasurface/material/RF performance claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
