from __future__ import annotations

import hashlib

from worldshepherd_sara.claims_linter_external import (
    EXTERNAL_LINTER_VERSION,
    build_external_lint_report,
    lint_external_claim,
)
from worldshepherd_sara.claims_linter_physics import LintSeverity


def _severity(findings, rule_id: str):
    return [item.severity for item in findings if item.rule_id == rule_id]


def test_self_applied_top_secret_marking_blocks():
    findings = lint_external_claim(
        "TOP SECRET // SPECIAL ACCESS REQUIRED — Worldshepherd program brief"
    )
    assert LintSeverity.BLOCK in _severity(findings, "EXT-CLASS-01")


def test_classification_denial_is_informational():
    findings = lint_external_claim(
        "This material is not classified; no TOP SECRET status is claimed or established."
    )
    assert LintSeverity.BLOCK not in _severity(findings, "EXT-CLASS-01")
    assert LintSeverity.INFO in _severity(findings, "EXT-CLASS-01")


def test_government_program_association_blocks_without_evidence_context():
    findings = lint_external_claim(
        "Department of War / Joint Technology Initiative — Worldshepherd"
    )
    assert LintSeverity.BLOCK in _severity(findings, "EXT-GOV-01")


def test_partnership_status_blocks_without_documentary_context():
    findings = lint_external_claim("Worldshepherd is in partnership with NIST.")
    assert LintSeverity.BLOCK in _severity(findings, "EXT-REL-01")


def test_negated_partnership_statement_is_informational():
    findings = lint_external_claim(
        "Worldshepherd does not claim partnership with NIST or any government endorsement."
    )
    assert LintSeverity.BLOCK not in _severity(findings, "EXT-REL-01")
    assert LintSeverity.INFO in _severity(findings, "EXT-REL-01")


def test_cmmc_certification_claim_blocks():
    findings = lint_external_claim("Worldshepherd is CMMC Level 2 certified.")
    assert LintSeverity.BLOCK in _severity(findings, "EXT-COMPLY-01")


def test_dr_brandon_davis_identity_block_blocks():
    findings = lint_external_claim("Dr. Brandon Ray Davis, Founder of Worldshepherd")
    assert LintSeverity.BLOCK in _severity(findings, "EXT-TITLE-01")


def test_title_accuracy_denial_does_not_trigger_false_block():
    findings = lint_external_claim(
        "Brandon Ray Davis does not claim the title Dr.; Brandon or Mr. Davis is appropriate."
    )
    assert LintSeverity.BLOCK not in _severity(findings, "EXT-TITLE-01")


def test_unqualified_external_maturity_language_fails_closed():
    findings = lint_external_claim(
        "Worldshepherd is production-ready and operationally validated."
    )
    assert LintSeverity.BLOCK in _severity(findings, "MATURITY-01")


def test_bounded_negative_maturity_language_stays_nonblocking():
    findings = lint_external_claim(
        "Worldshepherd is not production-ready and is not operationally validated."
    )
    assert LintSeverity.BLOCK not in _severity(findings, "MATURITY-01")


def test_report_binds_exact_input_and_counts_blocks():
    text = "Worldshepherd is in partnership with NIST."
    report = build_external_lint_report(text)
    assert report.schema_version == EXTERNAL_LINTER_VERSION
    assert report.input_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert report.blocked is True
    assert report.finding_counts["BLOCK"] >= 1


def test_report_is_nonblocking_for_plain_bounded_statement():
    text = (
        "Worldshepherd implements bounded workflow and evidence-provenance software. "
        "Independent external validation remains required for partner-owned physical capability."
    )
    report = build_external_lint_report(text)
    assert report.blocked is False
