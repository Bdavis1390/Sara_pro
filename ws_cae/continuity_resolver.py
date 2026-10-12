"""Fail-closed resolver from stable subject identity to current continuity state."""

from __future__ import annotations

from dataclasses import dataclass

from .continuity_lineage import assess_lineage
from .continuity_transition import ContinuityTransition


@dataclass(frozen=True)
class Resolution:
    resolved: bool
    subject_id: str
    current_content_id: str | None
    current_manifest: dict | None
    issues: tuple[str, ...]


def resolve(
    *,
    subject_id: str,
    genesis_content_id: str,
    transitions: tuple[ContinuityTransition, ...],
    manifests_by_content_id: dict[str, dict],
) -> Resolution:
    subject_id = subject_id.strip()
    issues: list[str] = []
    if not subject_id:
        return Resolution(False, "", None, None, ("subject_id must be non-empty",))

    lineage = assess_lineage(transitions, genesis_content_id=genesis_content_id)
    if not lineage.valid:
        issues.extend(lineage.issues)
    if transitions and lineage.subject_id != subject_id:
        issues.append("lineage subject_id does not match requested subject_id")
    if len(lineage.tip_content_ids) != 1:
        issues.append("lineage must resolve to exactly one terminal state")

    tip = lineage.tip_content_ids[0] if len(lineage.tip_content_ids) == 1 else None
    manifest = manifests_by_content_id.get(tip) if tip else None
    if tip and manifest is None:
        issues.append("terminal continuity manifest is unavailable")
    if manifest is not None:
        if not manifest.get("valid"):
            issues.append("terminal continuity manifest is invalid")
        payload = manifest.get("manifest") or {}
        if str(payload.get("subject_id", "")).strip() != subject_id:
            issues.append("terminal manifest subject_id does not match requested subject_id")
        if str(manifest.get("content_id", "")) != tip:
            issues.append("terminal manifest content_id does not match lineage tip")

    if issues:
        return Resolution(False, subject_id, tip, manifest, tuple(issues))
    return Resolution(True, subject_id, tip, manifest, tuple())
