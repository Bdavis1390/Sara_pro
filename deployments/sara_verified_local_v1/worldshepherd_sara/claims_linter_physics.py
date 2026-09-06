from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field

from .physics_validation import (
    ApprovalState,
    IndependentReviewState,
    PhysicsVerificationRecord,
    ValidationState,
)


class LintSeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    BLOCK = "BLOCK"


class LintFinding(BaseModel):
    rule_id: str = Field(min_length=1)
    severity: LintSeverity
    matched_text: str = Field(min_length=1)
    message: str = Field(min_length=1)
    safe_replacement: str | None = None


_BLOCK_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("PROP-01", re.compile(r"\b(reactionless propulsion|free[ -]?energy|over[ -]?unity|antigravity|gravity control)\b", re.I), "Current policy blocks propulsion/energy claims that bypass established conservation and validation gates."),
    ("QCOM-02", re.compile(r"\b(faster[ -]?than[ -]?light|instantaneous)\b.{0,40}\b(communication|messaging|quantum link)\b", re.I), "No-signaling and causal-channel accounting are required."),
    ("UFR-02", re.compile(r"\bstandard model\b.{0,40}\b(includes|contains|unifies)\b.{0,30}\bgravity\b", re.I), "The Standard Model does not include a quantum theory of gravity."),
    ("HIGGS-03", re.compile(r"\bhiggs\b.{0,50}\b(causes gravity|cause of gravity|all mass)\b", re.I), "Higgs language cannot be used as a blanket explanation of gravity or all mass."),
    ("MATURITY-ABS", re.compile(r"\b(100% secure|unhackable|guaranteed|perfectly safe)\b", re.I), "Absolute performance or safety claims require a domain-specific proof and are not permitted by default."),
)

_WARN_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("Q-01", re.compile(r"\b(quantum|entanglement|tunneling|higgs|standard model|lagrangian)\b", re.I), "Physics-bearing terminology requires a named mechanism, model scope, and measurable implication."),
    ("RES-01", re.compile(r"\b(resonance|harmonic resonance|coherence)\b", re.I), "Resonance/coherence must identify the physical mode, boundaries, damping or noise, and measurable response."),
    ("EM-01", re.compile(r"\b(electromagnetic energy|beam steering|metasurface|spectrum control)\b", re.I), "Electromagnetic capability should declare operating band, geometry, loss/efficiency, power, and validation status."),
    ("MATURITY-01", re.compile(r"\b(proven|validated|verified|certified|flight ready|production ready|clinically validated|combat proven)\b", re.I), "Maturity language must not exceed the registered validation and review state."),
)

_ALLOWED_QUALIFIERS = (
    "concept-stage",
    "architecture-level",
    "literature-supported",
    "simulated only",
    "synthetic scenario",
    "internally tested",
    "not independently replicated",
    "requires laboratory validation",
    "no measured worldshepherd-specific performance claimed",
)


def lint_physics_claim(
    text: str,
    *,
    record: PhysicsVerificationRecord | None = None,
) -> list[LintFinding]:
    findings: list[LintFinding] = []

    for rule_id, pattern, message in _BLOCK_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                LintFinding(
                    rule_id=rule_id,
                    severity=LintSeverity.BLOCK,
                    matched_text=match.group(0),
                    message=message,
                    safe_replacement="Use a bounded observation/model statement and identify the unresolved evidence gate.",
                )
            )

    qualifier_present = any(item in text.lower() for item in _ALLOWED_QUALIFIERS)
    for rule_id, pattern, message in _WARN_PATTERNS:
        for match in pattern.finditer(text):
            severity = LintSeverity.WARN
            if rule_id == "MATURITY-01" and record is not None:
                mature = record.validation_state in {
                    ValidationState.INDEPENDENTLY_REPLICATED,
                    ValidationState.QUALIFIED,
                    ValidationState.CERTIFIED,
                }
                reviewed = record.independent_review_state == IndependentReviewState.COMPLETED
                approved = record.cre1aws_approval_state == ApprovalState.APPROVED
                if not (mature and reviewed and approved):
                    severity = LintSeverity.BLOCK
            elif qualifier_present:
                severity = LintSeverity.INFO
            findings.append(
                LintFinding(
                    rule_id=rule_id,
                    severity=severity,
                    matched_text=match.group(0),
                    message=message,
                    safe_replacement="State the model scope, evidence class, operating conditions, uncertainty, and unresolved validation requirement.",
                )
            )

    # C3 governance lock is independent of terminology matching.
    if record is not None and record.claim_class > 3:
        if not (
            record.cre1aws_approval_state == ApprovalState.APPROVED
            and record.evidence_package_refs
            and record.audit_event_ids
        ):
            findings.append(
                LintFinding(
                    rule_id="MATURITY-02",
                    severity=LintSeverity.BLOCK,
                    matched_text="claim_class>C3",
                    message="Claims above C3 require registry evidence, audit evidence, and CRE1AWS approval.",
                )
            )

    # Stable ordering supports deterministic tests and audit diffs.
    return sorted(findings, key=lambda item: (item.severity.value, item.rule_id, item.matched_text.lower()))
