"""Bounded BAROS research-decision audit binding.

NON-CLINICAL and NON-AUTHENTICATING. This utility binds a *supplied* evidence
digest, state, thresholds and decision to one replayable audit record. SHA-256
is an integrity fingerprint, not a signature, proof of independent source data,
certification, radiotherapy authorization or proof of correct biological input.
Do NOT include patient identifiers or PHI in public records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import re

from .closed_loop import (
    AdaptationThresholds,
    BiologicalState,
    decide_adaptation,
)


SCHEMA = "baros.research-decision-audit.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_hash(payload: object) -> str:
    data = json.dumps(
        payload,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _require_digest(name: str, value: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 hexadecimal digest")


def _require_id(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty identifier")
    if len(value) > 96 or any(x in value for x in ("/", "\\", "\n", "\r")):
        raise ValueError(f"{name} must be a short public-safe identifier")


@dataclass(frozen=True)
class ResearchDecisionAudit:
    """Hash-bound, non-clinical decision; contains no biological arrays or patient data."""

    schema: str
    intended_use_id: str
    case_token: str
    source_evidence_sha256: str
    prior_state_sha256: str
    observed_state_sha256: str
    thresholds_sha256: str
    decision_sha256: str
    audit_sha256: str
    action: str
    phase_index: int
    proposal_allowed: bool
    treatment_authority: bool

    def public_metadata(self) -> dict[str, object]:
        return asdict(self)


def make_research_decision_audit(
    *,
    intended_use_id: str,
    case_token: str,
    source_evidence_sha256: str,
    previous: BiologicalState,
    current: BiologicalState,
    thresholds: AdaptationThresholds,
    last_valid_plan_identity: str | None,
    standard_plan_identity: str,
    manual_force: bool = False,
) -> ResearchDecisionAudit:
    """Recompute the actual BAROS decision and bind to supplied provenance.

    A caller-supplied digest is NOT proof of data rights or independently
    controlled data. No TPS or clinical operation occurs.
    """
    _require_id("intended_use_id", intended_use_id)
    _require_id("case_token", case_token)
    _require_digest("source_evidence_sha256", source_evidence_sha256)
    decision = decide_adaptation(
        previous=previous,
        current=current,
        thresholds=thresholds,
        last_valid_plan_identity=last_valid_plan_identity,
        standard_plan_identity=standard_plan_identity,
        manual_force=manual_force,
    )
    if decision.treatment_authority:
        raise ValueError("BAROS research audit cannot encode treatment authority")
    binding = {
        "schema": SCHEMA,
        "intended_use_id": intended_use_id,
        "case_token": case_token,
        "source_evidence_sha256": source_evidence_sha256,
        "prior_state_sha256": _canonical_hash(asdict(previous)),
        "observed_state_sha256": _canonical_hash(asdict(current)),
        "thresholds_sha256": _canonical_hash(asdict(thresholds)),
        "decision_sha256": _canonical_hash({
            "decision": asdict(decision),
            "manual_force": bool(manual_force),
        }),
        "action": decision.action,
        "phase_index": current.phase_index,
        "proposal_allowed": decision.proposal_allowed,
        "treatment_authority": decision.treatment_authority,
    }
    return ResearchDecisionAudit(**binding, audit_sha256=_canonical_hash(binding))


def verify_research_decision_audit(
    record: ResearchDecisionAudit, *,
    source_evidence_sha256: str,
    previous: BiologicalState,
    current: BiologicalState,
    thresholds: AdaptationThresholds,
    last_valid_plan_identity: str | None,
    standard_plan_identity: str,
    manual_force: bool = False,
) -> bool:
    """Replay bounded software policy and compare integrity fingerprints.

    Returns False on altered source, policy, state or decision. Does not
    authenticate the writer, evidence origin, clocks, chain-of-custody or TPS.
    """
    if not isinstance(record, ResearchDecisionAudit) or record.schema != SCHEMA:
        return False
    try:
        expected = make_research_decision_audit(
            intended_use_id=record.intended_use_id,
            case_token=record.case_token,
            source_evidence_sha256=source_evidence_sha256,
            previous=previous,
            current=current,
            thresholds=thresholds,
            last_valid_plan_identity=last_valid_plan_identity,
            standard_plan_identity=standard_plan_identity,
            manual_force=manual_force,
        )
    except (ValueError, TypeError, OverflowError):
        return False
    return hmac.compare_digest(
        json.dumps(asdict(record), sort_keys=True, allow_nan=False),
        json.dumps(asdict(expected), sort_keys=True, allow_nan=False),
    )
