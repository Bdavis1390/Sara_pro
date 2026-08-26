from __future__ import annotations

from typing import Any

from .horizons import CapabilityHorizonPortfolio, CapabilityHorizonRecord
from .qualification import ForecastHorizon, canonical_digest
from .readiness import CapabilityReadinessRecord, ReadinessRung


def _software_readiness(capability_id: str, name: str, bundle_digest: str, fixture_ref: str) -> CapabilityReadinessRecord:
    return CapabilityReadinessRecord(
        capability_id=capability_id,
        capability_name=name,
        highest_supported_rung=ReadinessRung.INTERNAL_SOFTWARE,
        evidence_refs={
            ReadinessRung.SCHEMA: ["qualification.py"],
            ReadinessRung.FIXTURE: [fixture_ref],
            ReadinessRung.INTERNAL_SOFTWARE: [bundle_digest],
        },
        blocked_next_rung=ReadinessRung.SIMULATION,
        missing_evidence=["representative validated simulation beyond frozen synthetic fixture"],
        claims_boundary=["Readiness applies only to the bounded implementation and evidence references listed here."],
    )


def build_readiness_ledger(bundle_digests: dict[str, str]) -> dict[str, Any]:
    records = [
        _software_readiness("CAP-APNT", "Synthetic APNT bounded awareness", bundle_digests["apnt"], "WS-APNT-SYNTH-001"),
        _software_readiness("CAP-MBSE", "Synthetic source-traceable MBSE extraction", bundle_digests["mbse"], "WS-MBSE-SYNTH-001"),
        _software_readiness("CAP-IETM", "Synthetic technical-data XML projection", bundle_digests["ietm"], "WS-IETM-SYNTH-001"),
        _software_readiness("CAP-ADE", "Synthetic interpretable algorithm discovery", bundle_digests["ade"], "WS-ADE-SYNTH-001"),
        _software_readiness("CAP-MISSION", "Synthetic mission replay/debrief", bundle_digests["mission"], "WS-MISSION-REPLAY-SYNTH-001"),
        _software_readiness("CAP-FUSION", "Synthetic provenance-preserving sensor fusion", bundle_digests["fusion"], "WS-FUSION-SYNTH-001"),
        _software_readiness("CAP-CBM", "Synthetic CBM+ health-state classification", bundle_digests["cbm"], "WS-CBM-SYNTH-001"),
        _software_readiness("CAP-MFG", "Manufacturing digital-thread lineage", bundle_digests["manufacturing"], "WS-MFG-THREAD-SYNTH-001"),
        _software_readiness("CAP-DDIL", "Synthetic DDIL transport-fault handling", bundle_digests["ddil"], "DDIL_SYNTHETIC_V1"),
    ]
    rf = CapabilityReadinessRecord(
        capability_id="CAP-RF-DISCREPANCY",
        capability_name="Synthetic RF simulation-to-measurement discrepancy accounting",
        highest_supported_rung=ReadinessRung.SIMULATION,
        evidence_refs={
            ReadinessRung.SCHEMA: ["qualification.py", "discrepancy.py"],
            ReadinessRung.FIXTURE: ["WS-RF-SYNTH-001"],
            ReadinessRung.INTERNAL_SOFTWARE: ["rf_validation.py"],
            ReadinessRung.SIMULATION: [bundle_digests["rf"]],
        },
        blocked_next_rung=ReadinessRung.HIL,
        missing_evidence=["fabricated RF coupon", "VNA/chamber measurements", "measurement-system calibration evidence"],
        claims_boundary=["Synthetic RF values only; no physical measurement or fabricated metasurface evidence."],
    )
    records.append(rf)
    value = {
        "schema": "WS-CAPABILITY-READINESS-LEDGER-V1",
        "records": [record.model_dump(mode="json") for record in records],
        "claims_boundary": [
            "Readiness rungs are evidence gates, not marketing maturity scores.",
            "No record may inherit a higher rung without corresponding evidence.",
        ],
    }
    value["ledger_digest"] = canonical_digest(value)
    return value


def build_horizon_portfolio() -> dict[str, Any]:
    records = [
        CapabilityHorizonRecord(horizon_id="H-APNT-0-90", capability_id="CAP-APNT", horizon=ForecastHorizon.D0_90, prerequisite_rung=ReadinessRung.INTERNAL_SOFTWARE, target_rung=ReadinessRung.SIMULATION, requirement_delta_ids=["PRE-RD-2026-0001"], build_actions=["implement authoritative-spec-gated APNT mapping contract using actual ASPN/pntOS definitions"], experiments=["representative source-fault simulation and operator workflow study"], partner_actions=["secure APNT interface/validation partner"], evidence_targets=["simulation qualification bundle", "interface conformance record"], blocking_conditions=["authoritative interface definitions and partner data required"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-DDIL-0-90", capability_id="CAP-DDIL", horizon=ForecastHorizon.D0_90, prerequisite_rung=ReadinessRung.INTERNAL_SOFTWARE, target_rung=ReadinessRung.SIMULATION, requirement_delta_ids=["PRE-RD-2026-0019"], build_actions=["integrate partition/rejoin reconciliation into mission/C2 simulation"], experiments=["network partition, delayed event, conflict and rejoin campaign"], evidence_targets=["reconciliation qualification bundle"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-MBSE-0-90", capability_id="CAP-MBSE", horizon=ForecastHorizon.D0_90, prerequisite_rung=ReadinessRung.INTERNAL_SOFTWARE, target_rung=ReadinessRung.SIMULATION, requirement_delta_ids=["PRE-RD-2026-0002"], build_actions=["add authorized PDF/image/diagram ingestion", "complete neutral-model validation before SysML export"], experiments=["holdout reconstruction benchmark with unsupported-inference scoring"], partner_actions=["obtain representative legacy-engineering artifact set"], evidence_targets=["holdout benchmark bundle"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-ADE-0-90", capability_id="CAP-ADE", horizon=ForecastHorizon.D0_90, prerequisite_rung=ReadinessRung.INTERNAL_SOFTWARE, target_rung=ReadinessRung.SIMULATION, requirement_delta_ids=["PRE-RD-2026-0012"], build_actions=["add noisy holdout, multivariable and constrained symbolic-discovery benchmarks"], experiments=["compare against fixed polynomial/symbolic baselines"], partner_actions=["identify research-institution independent benchmark partner"], evidence_targets=["multi-family discovery benchmark"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-FUSION-0-90", capability_id="CAP-FUSION", horizon=ForecastHorizon.D0_90, prerequisite_rung=ReadinessRung.INTERNAL_SOFTWARE, target_rung=ReadinessRung.SIMULATION, requirement_delta_ids=["PRE-RD-2026-0014"], build_actions=["add crossing tracks, false alarms, missed detections and covariance propagation"], experiments=["DDIL out-of-sequence fusion benchmark"], evidence_targets=["multi-target simulation bundle"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-CBM-3-12", capability_id="CAP-CBM", horizon=ForecastHorizon.M3_12, prerequisite_rung=ReadinessRung.SIMULATION, target_rung=ReadinessRung.HIL, build_actions=["adapter for real test-asset telemetry"], experiments=["sensor-in-loop fault injection"], partner_actions=["maintenance/test-asset partner"], evidence_targets=["HIL telemetry provenance bundle"], blocking_conditions=["requires prior representative simulation gate"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-MFG-3-12", capability_id="CAP-MFG", horizon=ForecastHorizon.M3_12, prerequisite_rung=ReadinessRung.HIL, target_rung=ReadinessRung.PHYSICAL_LAB, build_actions=["bind machine telemetry and material certificates to coupon lineage"], experiments=["fabricate and measure controlled coupons"], partner_actions=["DED machine/material characterization facility"], evidence_targets=["physical coupon measurement bundle"], blocking_conditions=["machine access, calibrated measurement and material lot evidence"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-RF-3-12", capability_id="CAP-RF-DISCREPANCY", horizon=ForecastHorizon.HIL if False else ForecastHorizon.M3_12, prerequisite_rung=ReadinessRung.HIL, target_rung=ReadinessRung.PHYSICAL_LAB, build_actions=["fabricate controlled RF/metasurface coupon"], experiments=["calibrated VNA/chamber comparison against frozen simulation"], partner_actions=["RF measurement/fabrication partner"], evidence_targets=["physical discrepancy bundle with calibration provenance"], blocking_conditions=["fabrication and calibrated RF facility"], forecast_only=True),
        CapabilityHorizonRecord(horizon_id="H-CROSS-12-24", capability_id="CAP-CROSS-DOMAIN", horizon=ForecastHorizon.M12_24_PLUS, prerequisite_rung=ReadinessRung.PARTNER, target_rung=ReadinessRung.INDEPENDENT, build_actions=["standardize independent reproduction packages across mature lanes"], experiments=["third-party blind reruns"], partner_actions=["independent labs/testbeds/government-authorized evaluators"], evidence_targets=["independent validation records"], blocking_conditions=["requires partner-rung evidence first"], forecast_only=True),
    ]
    portfolio = CapabilityHorizonPortfolio(records=records)
    value = {
        "schema": "WS-PRE-CAPABILITY-HORIZONS-V1",
        "records": [record.model_dump(mode="json") for record in portfolio.records],
        "immediate_actions": portfolio.immediate_actions(),
        "claims_boundary": [
            "Forecast horizon records schedule preparation only and never upgrade capability status.",
            "Every planned readiness transition remains blocked until the stated prerequisite evidence exists.",
        ],
    }
    value["portfolio_digest"] = canonical_digest(value)
    return value
