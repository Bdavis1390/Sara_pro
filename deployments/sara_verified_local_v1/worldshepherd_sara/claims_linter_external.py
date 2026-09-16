from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from pydantic import BaseModel, Field

from .claims_linter_physics import LintFinding, LintSeverity, lint_physics_claim
from .physics_validation import PhysicsVerificationRecord


EXTERNAL_LINTER_VERSION = "ws-external-claims-lint-1"


class ExternalLintReport(BaseModel):
    schema_version: str = EXTERNAL_LINTER_VERSION
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    blocked: bool
    finding_counts: dict[str, int]
    findings: list[LintFinding]


_EXTERNAL_BLOCK_PATTERNS: tuple[
    tuple[str, re.Pattern[str], str, str], ...
] = (
    (
        "EXT-CLASS-01",
        re.compile(
            r"\b(TOP SECRET|SECRET|CONFIDENTIAL|CUI|CONTROLLED UNCLASSIFIED INFORMATION|"
            r"SPECIAL ACCESS PROGRAM|SPECIAL ACCESS REQUIRED|SAP|classified)\b",
            re.I,
        ),
        "Government classification, CUI, SAP, or clearance-related language requires an authorized basis and must not be self-applied.",
        "Remove the marking or state the actual unclassified/public handling boundary unless an authorized source requires otherwise.",
    ),
    (
        "EXT-GOV-01",
        re.compile(
            r"(?:\b(?:official|authorized|approved|sponsored|endorsed)\s+(?:by\s+)?(?:the\s+)?"
            r"(?:U\.?S\.?\s+)?(?:government|Department of (?:Defense|War)|War Department|DoD|Navy|Army|"
            r"Air Force|Space Force|NASA|DOE|NIST|NIH|DARPA)\b|"
            r"\b(?:government|DoD|Department of (?:Defense|War)|War Department|Navy|Army|Air Force|Space Force|"
            r"NASA|DOE|NIST|NIH|DARPA)[ -](?:approved|sponsored|authorized|endorsed)\b|"
            r"\b(?:Department of War|War Department)\s*/?\s*(?:Joint Technology Initiative|program|initiative|office)\b)",
            re.I,
        ),
        "Government sponsorship, authorization, endorsement, office, or program-association language requires documentary evidence.",
        "Name the public opportunity or agency only as a target/context unless a documented relationship actually exists.",
    ),
    (
        "EXT-REL-01",
        re.compile(
            r"\b(in partnership with|partnered with|official partner of|endorsed by|selected by|awarded by|"
            r"under contract with|contracted by|customer of)\b",
            re.I,
        ),
        "Partnership, endorsement, selection, award, contract, or customer-status language requires documentary evidence.",
        "Describe outreach, interest, referral, application, or evaluation status exactly as the evidence supports.",
    ),
    (
        "EXT-COMPLY-01",
        re.compile(
            r"\b(?:CMMC(?:\s+Level\s+\d+)?|NIST\s+SP\s+800-171|DFARS)\s*[- ]?"
            r"(?:compliant|certified|approved)\b",
            re.I,
        ),
        "Compliance/certification language requires the applicable external or contractual evidence; internal controls are not sufficient by themselves.",
        "State the current readiness/gap status and the external assessment or authorization still required.",
    ),
    (
        "EXT-TITLE-01",
        re.compile(
            r"\bDr\.?\s+Brandon(?:\s+Ray)?\s+Davis\b|"
            r"\bBrandon(?:\s+Ray)?\s+Davis\s*,\s*(?:Ph\.?D\.?|Doctor of\b)",
            re.I,
        ),
        "Brandon Ray Davis does not currently claim an earned doctoral title or doctorate credential.",
        "Use 'Brandon Davis', 'Brandon Ray Davis', or 'Mr. Davis' unless an applicable qualified body formally confers a title.",
    ),
)


_NEGATION_BEFORE = re.compile(
    r"\b(?:no|not|never|without|does\s+not|do\s+not|is\s+not|are\s+not|"
    r"was\s+not|were\s+not|not\s+currently)\b(?:\W+\w+){0,6}\W*$",
    re.I,
)
_NEGATION_AFTER = re.compile(
    r"^.{0,80}\b(?:is|are|was|were|has|have)?\s*(?:not|never)\s+"
    r"(?:claimed|established|demonstrated|supported|authorized|certified|confirmed)\b",
    re.I,
)


def _explicit_external_denial(text: str, match: re.Match[str]) -> bool:
    before = text[max(0, match.start() - 120) : match.start()]
    after = text[match.end() : min(len(text), match.end() + 120)]
    return bool(_NEGATION_BEFORE.search(before) or _NEGATION_AFTER.search(after))


def _externalize_base_finding(finding: LintFinding) -> LintFinding:
    """Make unsupported maturity/clinical language fail closed in outbound text.

    The underlying physics linter can use a record to prove maturity. External drafts often
    arrive without one, so an unqualified maturity/clinical warning is escalated to BLOCK.
    Explicit denials and accepted limiting qualifiers are already INFO and stay unchanged.
    """
    if (
        finding.severity == LintSeverity.WARN
        and finding.rule_id in {"MATURITY-01", "MED-01"}
    ):
        return finding.model_copy(
            update={
                "severity": LintSeverity.BLOCK,
                "message": (
                    finding.message
                    + " External correspondence must supply a bounded evidence context before release."
                ),
            }
        )
    return finding


def lint_external_claim(
    text: str,
    *,
    record: PhysicsVerificationRecord | None = None,
) -> list[LintFinding]:
    findings = [
        _externalize_base_finding(item)
        for item in lint_physics_claim(text, record=record)
    ]

    for rule_id, pattern, message, safe_replacement in _EXTERNAL_BLOCK_PATTERNS:
        for match in pattern.finditer(text):
            denied = _explicit_external_denial(text, match)
            findings.append(
                LintFinding(
                    rule_id=rule_id,
                    severity=LintSeverity.INFO if denied else LintSeverity.BLOCK,
                    matched_text=match.group(0),
                    message=(
                        "Term appears inside explicit claim-denial/limiting language."
                        if denied
                        else message
                    ),
                    safe_replacement=None if denied else safe_replacement,
                )
            )

    severity_order = {
        LintSeverity.BLOCK: 0,
        LintSeverity.WARN: 1,
        LintSeverity.INFO: 2,
    }
    return sorted(
        findings,
        key=lambda item: (
            severity_order[item.severity],
            item.rule_id,
            item.matched_text.lower(),
        ),
    )


def build_external_lint_report(
    text: str,
    *,
    record: PhysicsVerificationRecord | None = None,
) -> ExternalLintReport:
    findings = lint_external_claim(text, record=record)
    counts = {
        severity.value: sum(item.severity == severity for item in findings)
        for severity in LintSeverity
    }
    return ExternalLintReport(
        input_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        blocked=counts[LintSeverity.BLOCK.value] > 0,
        finding_counts=counts,
        findings=findings,
    )


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed claims lint for Worldshepherd external correspondence."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="UTF-8 draft file to lint, or '-' for stdin (default).",
    )
    args = parser.parse_args(argv)

    report = build_external_lint_report(_read_text(args.path))
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    if report.blocked:
        return 2
    if report.finding_counts[LintSeverity.WARN.value]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
