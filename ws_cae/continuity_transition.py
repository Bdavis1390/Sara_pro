"""Content-addressed state transitions for WS-CAE continuity manifests.

A transition links two immutable continuity-manifest states for the same stable
subject. Metadata only: no keys, signatures, transactions, consensus, or assets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

REASONS = {
    "ALGORITHM_MIGRATION",
    "AUTHORITY_ROTATION",
    "DEPENDENCY_CHANGE",
    "RECOVERY_CHANGE",
    "GOVERNANCE_CHANGE",
    "EVIDENCE_UPDATE",
    "OTHER",
}


@dataclass(frozen=True)
class ContinuityTransition:
    subject_id: str
    previous_content_id: str
    new_content_id: str
    reason: str
    effective_at: str
    evidence_refs: tuple[str, ...] = tuple()

    def to_dict(self) -> dict:
        return asdict(self)


def _valid_content_id(value: str) -> bool:
    if not value.startswith("sha256:") or len(value) != 71:
        return False
    try:
        bytes.fromhex(value[7:])
    except ValueError:
        return False
    return True


def validate_transition(transition: ContinuityTransition) -> tuple[str, ...]:
    issues: list[str] = []
    if not transition.subject_id.strip():
        issues.append("subject_id must be non-empty")
    if not _valid_content_id(transition.previous_content_id):
        issues.append("previous_content_id is invalid")
    if not _valid_content_id(transition.new_content_id):
        issues.append("new_content_id is invalid")
    if transition.previous_content_id == transition.new_content_id:
        issues.append("transition must change content state")
    if transition.reason not in REASONS:
        issues.append("transition reason is not recognized")
    if not transition.effective_at.strip():
        issues.append("effective_at must be non-empty")
    if any(not ref.strip() for ref in transition.evidence_refs):
        issues.append("evidence_refs must not contain empty values")
    return tuple(issues)


def canonical_bytes(transition: ContinuityTransition) -> bytes:
    return json.dumps(transition.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def transition_id(transition: ContinuityTransition) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(transition)).hexdigest()


def from_envelopes(
    previous: dict,
    new: dict,
    *,
    reason: str,
    effective_at: str,
    evidence_refs: tuple[str, ...] = tuple(),
) -> ContinuityTransition:
    if not previous.get("valid") or not new.get("valid"):
        raise ValueError("both continuity manifests must be valid")
    prev_manifest = previous.get("manifest") or {}
    new_manifest = new.get("manifest") or {}
    subject = str(prev_manifest.get("subject_id", ""))
    if not subject or subject != str(new_manifest.get("subject_id", "")):
        raise ValueError("continuity transition requires the same stable subject_id")
    transition = ContinuityTransition(
        subject_id=subject,
        previous_content_id=str(previous.get("content_id", "")),
        new_content_id=str(new.get("content_id", "")),
        reason=reason,
        effective_at=effective_at,
        evidence_refs=evidence_refs,
    )
    issues = validate_transition(transition)
    if issues:
        raise ValueError("; ".join(issues))
    return transition
