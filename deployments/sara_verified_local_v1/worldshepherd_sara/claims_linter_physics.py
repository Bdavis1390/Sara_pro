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
    (
        "PROP-01",
        re.compile(
            r"\b(reactionless propulsion|free[ -]?energy|over[ -]?unity|antigravity|gravity[ -]?control)\b",
            re.I,
        ),
        "Current policy blocks propulsion/energy claims that bypass established conservation and validation gates.",
    ),
    (
        "QCOM-02",
        re.compile(
            r"\b(faster[ -]?than[ -]?light|instantaneous)\b.{0,40}\b(communication|messaging|quantum link)\b",
            re.I,
        ),
        "No-signaling and causal-channel accounting are required.",
    ),
    (
        "UFR-02",
        re.compile(
            r"\bstandard model\b.{0,40}\b(includes|contains|unifies)\b.{0,30}\bgravity\b",
            re.I,
        ),
        "The Standard Model does not include a quantum theory of gravity.",
    ),
    (
        "HIGGS-03",
        re.compile(r"\bhiggs\b.{0,50}\b(causes gravity|cause of gravity|all mass)\b", re.I),
        "Higgs language cannot be used as a blanket explanation of gravity or all mass.",
    ),
    (
        "MATURITY-ABS",
        re.compile(r"\b(100% secure|unhackable|guaranteed|perfectly safe)\b", re.I),
        "Absolute performance or safety claims require a domain-specific proof and are not permitted by default.",
    ),
)

_WARN_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "Q-01",
        re.compile(r"\b(quantum|entanglement|tunneling|higgs|standard model|lagrangian)\b", re.I),
        "Physics-bearing terminology requires a named mechanism, model scope, and measurable implication.",
    ),
    (
        "RES-01",
        re.compile(r"\b(resonance|harmonic resonance|coherence)\b", re.I),
        "Resonance/coherence must identify the physical mode, boundaries, damping or noise, and measurable response.",
    ),
    (
        "EM-01",
        re.compile(r"\b(electromagnetic energy|beam steering|metasurface|spectrum control)\b", re.I),
        "Electromagnetic capability should declare operating band, geometry, loss/efficiency, power, and validation status.",
    ),
    (
        "SENS-01",
        re.compile(
            r"\b(stealth|cloaking|low[ -]?observable|radar cross[ -]?section reduction|invisible to radar)\b",
            re.I,
        ),
        "Low-observable/scattering claims require calibrated measured hardware evidence, geometry, background control, and uncertainty.",
    ),
    (
        "MED-01",
        re.compile(
            r"\b(clinically proven|clinical-grade|patient-safe|treatment-ready|diagnostically proven)\b",
            re.I,
        ),
        "Clinical or patient-safety language requires the applicable qualified-domain, validation, regulatory, and governance evidence.",
    ),
    (
        "MATURITY-01",
        re.compile(
            r"\b(proven|validated|verified|certified|qualified|independently replicated|flight[ -]?ready|flight[ -]?tested|flight[ -]?proven|field[ -]?proven|operationally validated|production[ -]?ready|clinically validated|clinically proven|combat[ -]?proven)\b",
            re.I,
        ),
        "Maturity language must not exceed the registered validation and review state.",
    ),
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
    "requires lab validation",
    "no measured worldshepherd-specific performance claimed",
    "not clinically validated",
    "not flight ready",
    "not flight-ready",
    "not certified",
    "not qualified",
    "not proven",
    "not validated",
    "not verified",
)

_NEGATION_BEFORE = re.compile(
    r"\b(no|not|never|without|lacks?|lacking|neither)\b(?:\W+\w+){0,5}\W*$",
    re.I,
)
_NEGATION_AFTER = re.compile(
    r"^\W*(?:is|are|was|were|remains?|remain|has|have)?\W*"
    r"(?:not|never|unproven|unvalidated|unsupported|unverified|uncertified|unqualified)\b",
    re.I,
)
_CLAIM_DENIAL_AFTER = re.compile(
    r"^.{0,60}\b(?:is|are|was|were)?\s*(?:not\s+)?(?:claimed|established|demonstrated|supported)\b",
    re.I,
)


def _explicitly_negated(text: str, match: re.Match[str]) -> bool:
    """Recognize bounded claim-denial language without suppressing ordinary claims."""
    before = text[max(0, match.start() - 80) : match.start()]
    after = text[match.end() : min(len(text), match.end() + 100)]
    if _NEGATION_BEFORE.search(before):
        return True
    if _NEGATION_AFTER.search(after):
        return True
    # Handles constructions such as "reactionless propulsion is not claimed".
    if re.search(r"\bnot\b", after[:40], re.I) and _CLAIM_DENIAL_AFTER.search(after):
        return True
    return False


def _record_supports_maturity_language(record: PhysicsVerificationRecord) -> bool:
    mature = record.validation_state in {
        ValidationState.INDEPENDENTLY_REPLICATED,
        ValidationState.QUALIFIED,
        ValidationState.CERTIFIED,
    }
    reviewed = record.independent_review_state == IndependentReviewState.COMPLETED
    approved = record.cre1aws_approval_state == ApprovalState.APPROVED
    return mature and reviewed and approved


def lint_physics_claim(
    text: str,
    *,
    record: PhysicsVerificationRecord | None = None,
) -> list[LintFinding]:
    findings: list[LintFinding] = []

    for rule_id, pattern, message in _BLOCK_PATTERNS:
        for match in pattern.finditer(text):
            negated = _explicitly_negated(text, match)
            findings.append(
                LintFinding(
                    rule_id=rule_id,
                    severity=LintSeverity.INFO if negated else LintSeverity.BLOCK,
                    matched_text=match.group(0),
                    message=(
                        "Term appears inside explicit claim-denial/limiting language."
                        if negated
                        else message
                    ),
                    safe_replacement=(
                        None
                        if negated
                        else "Use a bounded observation/model statement and identify the unresolved evidence gate."
                    ),
                )
            )

    qualifier_present = any(item in text.lower() for item in _ALLOWED_QUALIFIERS)
    for rule_id, pattern, message in _WARN_PATTERNS:
        for match in pattern.finditer(text):
            negated = _explicitly_negated(text, match)
            severity = LintSeverity.WARN
            if negated:
                severity = LintSeverity.INFO
            elif rule_id == "MATURITY-01" and record is not None:
                if not _record_supports_maturity_language(record):
                    severity = LintSeverity.BLOCK
            elif rule_id in {"MED-01"} and record is not None:
                if not _record_supports_maturity_language(record):
                    severity = LintSeverity.BLOCK
            elif qualifier_present:
                severity = LintSeverity.INFO
            findings.append(
                LintFinding(
                    rule_id=rule_id,
                    severity=severity,
                    matched_text=match.group(0),
                    message=(
                        "Term appears inside explicit claim-denial/limiting language."
                        if negated
                        else message
                    ),
                    safe_replacement=(
                        None
                        if negated
                        else "State the model scope, evidence class, operating conditions, uncertainty, and unresolved validation requirement."
                    ),
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
    severity_order = {
        LintSeverity.BLOCK: 0,
        LintSeverity.WARN: 1,
        LintSeverity.INFO: 2,
    }
    return sorted(
        findings,
        key=lambda item: (severity_order[item.severity], item.rule_id, item.matched_text.lower()),
    )
