from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure_assurance import (
    CLAIMS_BOUNDARY,
    PackageState,
    authorize_configuration_change,
    build_synthetic_packages,
    close_package,
    ingest_evidence,
    resolve_issue,
    run_gate,
)
from .infrastructure_assurance import _valid_evidence


INTERNAL_TARGET_PCT = 98.7
EXTERNAL_TARGET_PCT = 98.7
EXTERNAL_PREAUTH_CAP_PCT = 55.0

ALLOWED_DATA_CLASSES = {"PUBLIC", "SYNTHETIC"}
BLOCKED_DATA_CLASSES = {
    "FCI",
    "CUI",
    "CDI",
    "EXPORT_CONTROLLED",
    "CLASSIFIED",
    "UNKNOWN",
}

READINESS_CLAIMS_BOUNDARY = (
    "A passing Sentinel readiness report establishes only completion of the encoded internal synthetic "
    "preparation checks. It does not establish Sentinel fitness, USACE/Air Force acceptance, prime approval, "
    "field integration, construction qualification, CMMC/NIST conformity, SPRS score, clearance, CUI/CDI "
    "authorization, export authorization, NC3 access, weapon-control capability, operational effectiveness, "
    "partner interest, award probability, or deployment authority."
)


@dataclass(frozen=True)
class BoundaryDecision:
    data_class: str
    allowed: bool
    reason: str


def evaluate_data_boundary(data_class: str) -> BoundaryDecision:
    normalized = data_class.strip().upper()
    if normalized in ALLOWED_DATA_CLASSES:
        return BoundaryDecision(normalized, True, "allowed_for_synthetic_internal_gate")
    if normalized in BLOCKED_DATA_CLASSES or not normalized:
        return BoundaryDecision(normalized or "MISSING", False, "blocked_without_external_authorization_and_boundary")
    return BoundaryDecision(normalized, False, "unrecognized_class_fail_closed")


def run_scale_campaign(package_count: int = 2000) -> dict[str, Any]:
    if package_count < 1:
        raise ValueError("package_count must be positive")
    closed = 0
    false_blocks = 0
    unauthorized_attempts = 0
    unauthorized_mutations = 0
    packages = build_synthetic_packages(package_count)
    for package in packages:
        state = PackageState(package=package, current_baseline=package.baseline_id)
        for evidence_type in package.required_evidence_types:
            record = _valid_evidence(
                state,
                evidence_id=f"{package.package_id}-{evidence_type}",
                evidence_type=evidence_type,
                source_org=package.owner_org,
                source_actor="synthetic-operator",
            )
            accepted, findings = ingest_evidence(state, record)
            if not accepted or findings:
                false_blocks += 1
        did_close, blockers = close_package(state)
        if did_close and not blockers:
            closed += 1
        else:
            false_blocks += 1

        unauthorized_attempts += 1
        before = state.config_mutations
        event = authorize_configuration_change(
            state,
            actor="synthetic-field-operator",
            role="FIELD_OPERATOR",
            new_baseline="BL-UNAUTHORIZED",
        )
        if event.decision != "DENY" or state.config_mutations != before:
            unauthorized_mutations += 1

    return {
        "schema": "WS-SENTINEL-SCALE-CAMPAIGN-V1",
        "evidence_status": "INTERNAL_SYNTHETIC_SOFTWARE_EVIDENCE",
        "package_count": package_count,
        "closed_cleanly": closed,
        "false_blocks": false_blocks,
        "unauthorized_attempts": unauthorized_attempts,
        "unauthorized_authoritative_mutations": unauthorized_mutations,
        "pass": closed == package_count and false_blocks == 0 and unauthorized_mutations == 0,
        "claims_boundary": CLAIMS_BOUNDARY,
    }


def run_integrity_adversarial_campaign() -> dict[str, Any]:
    checks: dict[str, bool] = {}

    packages = build_synthetic_packages(2)
    state = PackageState(package=packages[0], current_baseline="BL-001")
    cross_package = _valid_evidence(state, evidence_id="ADV-XPKG", evidence_type="design")
    cross_package = cross_package.model_copy(update={"package_id": packages[1].package_id})
    accepted, findings = ingest_evidence(state, cross_package)
    checks["cross_package_rejected"] = not accepted and "PACKAGE_ID_MISMATCH" in findings

    state = PackageState(package=packages[0], current_baseline="BL-001")
    invalid = _valid_evidence(state, evidence_id="ADV-INVALID", evidence_type="design", valid=False)
    accepted, findings = ingest_evidence(state, invalid)
    checks["source_invalid_rejected"] = not accepted and "SOURCE_MARKED_INVALID" in findings

    state = PackageState(package=packages[0], current_baseline="BL-001")
    first = _valid_evidence(state, evidence_id="ADV-DUP", evidence_type="inspection")
    accepted_first, _ = ingest_evidence(state, first)
    accepted_second, findings_second = ingest_evidence(state, first)
    checks["duplicate_identity_rejected"] = (
        accepted_first and not accepted_second and "DUPLICATE_EVIDENCE_ID" in findings_second
    )

    state = PackageState(package=packages[0], current_baseline="BL-001")
    v1 = _valid_evidence(state, evidence_id="ADV-V1", evidence_type="as_built", version=1)
    ingest_evidence(state, v1)
    v2_bad = _valid_evidence(state, evidence_id="ADV-V2-BAD", evidence_type="as_built", version=2)
    accepted_bad, findings_bad = ingest_evidence(state, v2_bad)
    checks["supersession_chain_required"] = (
        not accepted_bad and "SUPERSESSION_CHAIN_MISSING" in findings_bad
    )

    state = PackageState(package=packages[0], current_baseline="BL-001")
    v1 = _valid_evidence(state, evidence_id="ADV-V1-GOOD", evidence_type="as_built", version=1)
    ingest_evidence(state, v1)
    v2_good = _valid_evidence(
        state,
        evidence_id="ADV-V2-GOOD",
        evidence_type="as_built",
        version=2,
        supersedes="ADV-V1-GOOD",
    )
    accepted_good, findings_good = ingest_evidence(state, v2_good)
    checks["valid_supersession_accepted"] = accepted_good and not findings_good

    state = PackageState(package=packages[0], current_baseline="BL-001")
    design = _valid_evidence(state, evidence_id="ADV-BASELINE", evidence_type="design")
    ingest_evidence(state, design)
    before = len(state.authoritative_evidence)
    event = authorize_configuration_change(
        state,
        actor="program-authority",
        role=state.package.authority_required,
        new_baseline="BL-002",
    )
    checks["baseline_change_invalidates_prior_authority"] = (
        before == 1
        and event.decision == "ALLOW"
        and state.current_baseline == "BL-002"
        and len(state.authoritative_evidence) == 0
    )

    state = PackageState(package=packages[0], current_baseline="BL-001")
    event = authorize_configuration_change(
        state,
        actor="field-operator",
        role="FIELD_OPERATOR",
        new_baseline="BL-002",
        approval_actor="claimed-approver",
    )
    checks["approver_name_cannot_bypass_role"] = (
        event.decision == "REQUIRE_APPROVAL"
        and state.current_baseline == "BL-001"
        and state.config_mutations == 0
    )

    state = PackageState(package=packages[0], current_baseline="BL-001")
    invalid = _valid_evidence(state, evidence_id="ADV-ISSUE", evidence_type="design", valid=False)
    ingest_evidence(state, invalid)
    denied = resolve_issue(
        state,
        issue="SOURCE_MARKED_INVALID",
        actor="field-operator",
        role="FIELD_OPERATOR",
        rationale="not authorized",
    )
    allowed = resolve_issue(
        state,
        issue="SOURCE_MARKED_INVALID",
        actor="program-authority",
        role=state.package.authority_required,
        rationale="synthetic review disposition for readiness test",
    )
    checks["issue_resolution_authority_enforced"] = (
        not denied and allowed and "SOURCE_MARKED_INVALID" not in state.issues
    )

    return {
        "schema": "WS-SENTINEL-INTEGRITY-ADVERSARIAL-CAMPAIGN-V1",
        "evidence_status": "INTERNAL_SYNTHETIC_SOFTWARE_EVIDENCE",
        "check_count": len(checks),
        "passed_count": sum(checks.values()),
        "checks": checks,
        "pass": all(checks.values()),
        "claims_boundary": READINESS_CLAIMS_BOUNDARY,
    }


def external_gate_matrix() -> dict[str, Any]:
    gates = [
        {
            "gate": "partner_or_prime_authorization",
            "state": "MISSING",
            "hard_cap_pct_if_not_closed": 55.0,
            "self_close_allowed": False,
            "minimum_external_evidence": [
                "written authorization or teaming direction from a legitimate prime/partner authority",
                "identified scope and permitted information classes",
            ],
        },
        {
            "gate": "program_specific_security_and_clause_applicability",
            "state": "MISSING",
            "hard_cap_pct_if_not_closed": 70.0,
            "self_close_allowed": False,
            "minimum_external_evidence": [
                "actual solicitation/subcontract security requirements",
                "authoritative FCI/CUI/CDI/export determination",
                "approved system/environment boundary where controlled information is involved",
            ],
        },
        {
            "gate": "controlled_partner_pilot",
            "state": "MISSING",
            "hard_cap_pct_if_not_closed": 82.0,
            "self_close_allowed": False,
            "minimum_external_evidence": [
                "authorized pilot sponsor and scope",
                "partner-approved ground truth and interfaces",
                "controlled execution record with source/configuration digests",
            ],
        },
        {
            "gate": "measured_partner_effect",
            "state": "MISSING",
            "hard_cap_pct_if_not_closed": 90.0,
            "self_close_allowed": False,
            "minimum_external_evidence": [
                "predeclared baseline/comparator",
                "measured effect with uncertainty and confounder review",
                "partner-approved endpoint ground truth",
            ],
        },
        {
            "gate": "independent_reproduction_or_acceptance",
            "state": "MISSING",
            "hard_cap_pct_if_not_closed": 97.0,
            "self_close_allowed": False,
            "minimum_external_evidence": [
                "independent reviewer or partner acceptance authority",
                "reproduction or acceptance record bound to retained evidence digests",
            ],
        },
    ]
    return {
        "schema": "WS-SENTINEL-EXTERNAL-GATE-MATRIX-V1",
        "target_external_readiness_pct": EXTERNAL_TARGET_PCT,
        "current_external_readiness_cap_pct": EXTERNAL_PREAUTH_CAP_PCT,
        "gates": gates,
        "claims_boundary": READINESS_CLAIMS_BOUNDARY,
    }


def build_readiness_report(*, scale_package_count: int = 2000) -> dict[str, Any]:
    gate = run_gate(campaign_id="WS-SENTINEL-READINESS-G1")
    scale = run_scale_campaign(scale_package_count)
    integrity = run_integrity_adversarial_campaign()
    boundary_results = [
        evaluate_data_boundary(item)
        for item in (
            "PUBLIC",
            "SYNTHETIC",
            "FCI",
            "CUI",
            "CDI",
            "EXPORT_CONTROLLED",
            "CLASSIFIED",
            "UNKNOWN",
            "UNLISTED",
        )
    ]
    boundary_pass = all(
        result.allowed if result.data_class in ALLOWED_DATA_CLASSES else not result.allowed
        for result in boundary_results
    )

    controls = {
        "failure_injection_gate": bool(gate.pass_gate),
        "ten_failure_classes_detected": gate.metrics.get("detected_failure_count") == 10,
        "safe_state_preserved": gate.metrics.get("safe_state_preserved_count") == 10,
        "zero_unauthorized_mutations_g1": gate.metrics.get("unauthorized_authoritative_mutations") == 0,
        "scale_campaign": bool(scale["pass"]),
        "integrity_adversarial_campaign": bool(integrity["pass"]),
        "data_boundary_fail_closed": boundary_pass,
        "claims_boundary_present": "does not establish" in READINESS_CLAIMS_BOUNDARY.lower(),
    }
    passed = sum(1 for value in controls.values() if value)
    total = len(controls)
    internal_pct = round((passed / total) * 100.0, 3)
    internal_gate_pass = internal_pct >= INTERNAL_TARGET_PCT

    return {
        "schema": "WS-SENTINEL-READINESS-REPORT-V1",
        "evidence_status": "INTERNAL_SYNTHETIC_SOFTWARE_EVIDENCE",
        "internal_preparation_target_pct": INTERNAL_TARGET_PCT,
        "internal_preparation_score_pct": internal_pct,
        "internal_preparation_gate_pass": internal_gate_pass,
        "internal_controls": controls,
        "scale_campaign": scale,
        "integrity_adversarial_campaign": integrity,
        "data_boundary": [result.__dict__ for result in boundary_results],
        "external_gate_matrix": external_gate_matrix(),
        "external_operational_readiness_cap_pct": EXTERNAL_PREAUTH_CAP_PCT,
        "external_operational_gate_pass": False,
        "decision": (
            "INTERNAL_PREPARATION_GATE_PASS_EXTERNAL_GATES_OPEN"
            if internal_gate_pass
            else "INTERNAL_PREPARATION_GATE_FAIL"
        ),
        "claims_boundary": READINESS_CLAIMS_BOUNDARY,
    }
