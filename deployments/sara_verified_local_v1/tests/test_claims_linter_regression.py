from __future__ import annotations

from worldshepherd_sara.claims_linter_physics import LintSeverity, lint_physics_claim
from worldshepherd_sara.physics_validation import PhysicsVerificationRecord


def concept_record(project_id: str = "WORLDSHEPHERD-CORE") -> PhysicsVerificationRecord:
    return PhysicsVerificationRecord(
        record_id="PHYS-LINT-REG-0001",
        artifact_id="ART-LINT-REG-0001",
        project_id=project_id,
        physics_domain=["electromagnetics"],
        model_scope="claim-linter regression fixture",
        assumptions=["concept stage"],
        validation_state="concept",
        claim_label="Hypothesis",
        claim_class=1,
        external_safe_statement="No measured Worldshepherd-specific performance claimed.",
        created_at="2026-09-07T00:40:00Z",
        updated_at="2026-09-07T00:40:00Z",
    )


def _severity(findings, rule_id: str):
    return [item.severity for item in findings if item.rule_id == rule_id]


def test_explicit_reactionless_denial_is_not_blocked():
    findings = lint_physics_claim(
        "No reactionless propulsion is claimed or established by this experiment.",
        record=concept_record("RESONANT_EM_PROPULSION"),
    )
    assert LintSeverity.BLOCK not in _severity(findings, "PROP-01")
    assert LintSeverity.INFO in _severity(findings, "PROP-01")


def test_reactionless_claim_without_negation_is_blocked():
    findings = lint_physics_claim(
        "This device demonstrates reactionless propulsion.",
        record=concept_record("RESONANT_EM_PROPULSION"),
    )
    assert LintSeverity.BLOCK in _severity(findings, "PROP-01")


def test_negated_clinical_maturity_is_not_blocked():
    findings = lint_physics_claim(
        "BAROS is not clinically validated and is not treatment-ready.",
        record=concept_record("BAROS"),
    )
    assert LintSeverity.BLOCK not in _severity(findings, "MATURITY-01")
    assert LintSeverity.BLOCK not in _severity(findings, "MED-01")


def test_positive_clinical_maturity_is_blocked_on_concept_record():
    findings = lint_physics_claim(
        "BAROS is clinically proven and treatment-ready.",
        record=concept_record("BAROS"),
    )
    assert LintSeverity.BLOCK in _severity(findings, "MATURITY-01")
    assert LintSeverity.BLOCK in _severity(findings, "MED-01")


def test_independent_replication_wording_requires_maturity():
    findings = lint_physics_claim(
        "The propulsion effect has been independently replicated.",
        record=concept_record("RESONANT_EM_PROPULSION"),
    )
    assert LintSeverity.BLOCK in _severity(findings, "MATURITY-01")


def test_negated_independent_replication_is_informational():
    findings = lint_physics_claim(
        "The effect has not been independently replicated.",
        record=concept_record("RESONANT_EM_PROPULSION"),
    )
    assert LintSeverity.BLOCK not in _severity(findings, "MATURITY-01")
    assert LintSeverity.INFO in _severity(findings, "MATURITY-01")


def test_flight_proven_wording_requires_maturity():
    findings = lint_physics_claim(
        "The AEROSHEPHERD vehicle is flight-proven and production-ready.",
        record=concept_record("AEROSHEPHERD"),
    )
    assert LintSeverity.BLOCK in _severity(findings, "MATURITY-01")


def test_low_observable_term_warns_without_false_maturity_upgrade():
    findings = lint_physics_claim(
        "The metasurface concept targets low-observable scattering behavior.",
        record=concept_record("ADAPTIVE_METASURFACE"),
    )
    assert LintSeverity.WARN in _severity(findings, "SENS-01")


def test_absolute_safety_denial_is_not_blocked():
    findings = lint_physics_claim(
        "The system is not guaranteed or perfectly safe; safety remains to be validated.",
        record=concept_record(),
    )
    assert LintSeverity.BLOCK not in _severity(findings, "MATURITY-ABS")
