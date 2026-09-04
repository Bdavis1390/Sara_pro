from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Iterable

from pydantic import BaseModel, Field

from .hmaa_lattice_capture import SandboxReadCaptureResult


HMAA_ATTESTATION_VERSION = "worldshepherd.hmaa.attestation.v0.7"
CANDIDATE_SOURCE_LABEL = "authorized-sandbox-readonly-candidate"
REPEATABLE_CAPTURE_THRESHOLD = 3


class HMAAAttestationState(str, Enum):
    NO_EVIDENCE = "NO_EVIDENCE"
    CANDIDATE_EVIDENCE = "CANDIDATE_EVIDENCE"
    EXTERNAL_ATTESTATION_REQUIRED = "EXTERNAL_ATTESTATION_REQUIRED"


class HMAACaptureReference(BaseModel):
    mission_id: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    fixture_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    final_chain_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_count: int = Field(gt=0)
    captured_entity_messages: int = Field(ge=0)
    captured_task_messages: int = Field(ge=0)
    disposition_counts: dict[str, int]
    capture_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class HMAAAttestationReport(BaseModel):
    attestation_version: str = HMAA_ATTESTATION_VERSION
    mission_id: str | None = None
    state: HMAAAttestationState
    capture_count: int = 0
    distinct_capture_count: int = 0
    repeatability_satisfied: bool = False
    aggregate_sha256: str | None = None
    live_environment_validated: bool = False
    external_attestation_required: bool = True
    claimable_labels: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    captures: list[HMAACaptureReference] = Field(default_factory=list)


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _capture_reference(capture: SandboxReadCaptureResult) -> HMAACaptureReference:
    manifest = capture.interop.manifest
    bundle = capture.interop.evidence_bundle

    if capture.live_environment_validated or manifest.live_environment_validated:
        raise ValueError(
            "candidate evidence must not assert live-environment validation"
        )
    if capture.source_label != CANDIDATE_SOURCE_LABEL:
        raise ValueError("capture source label is not the authorized Sandbox candidate label")
    if manifest.source_label != CANDIDATE_SOURCE_LABEL:
        raise ValueError("interop manifest source label is not the authorized Sandbox candidate label")

    sampled_count = capture.captured_entity_messages + capture.captured_task_messages
    if sampled_count <= 0:
        raise ValueError("capture must contain at least one sampled message")
    if manifest.event_count != sampled_count:
        raise ValueError("capture event count does not match sampled message count")
    if bundle.mission_id != manifest.mission_id:
        raise ValueError("capture bundle and manifest mission IDs do not match")
    if bundle.final_chain_hash is None or manifest.final_chain_hash is None:
        raise ValueError("capture is missing a final evidence-chain hash")
    if bundle.final_chain_hash != manifest.final_chain_hash:
        raise ValueError("capture bundle and manifest chain heads do not match")

    disposition_total = sum(manifest.disposition_counts.values())
    if disposition_total != manifest.event_count:
        raise ValueError("capture disposition counts do not match event count")
    non_allow = {
        name: count
        for name, count in manifest.disposition_counts.items()
        if name != "ALLOW" and count > 0
    }
    if non_allow:
        raise ValueError(
            "capture contains non-ALLOW assurance dispositions and requires review"
        )
    if manifest.disposition_counts.get("ALLOW", 0) != manifest.event_count:
        raise ValueError("capture is not fully ALLOW-qualified")

    digest_body = {
        "mission_id": manifest.mission_id,
        "source_label": manifest.source_label,
        "fixture_sha256": manifest.fixture_sha256,
        "final_chain_hash": manifest.final_chain_hash,
        "event_count": manifest.event_count,
        "captured_entity_messages": capture.captured_entity_messages,
        "captured_task_messages": capture.captured_task_messages,
        "disposition_counts": dict(sorted(manifest.disposition_counts.items())),
    }
    return HMAACaptureReference(
        **digest_body,
        capture_sha256=_sha256_json(digest_body),
    )


def attest_candidate_captures(
    captures: Iterable[SandboxReadCaptureResult],
    *,
    required_distinct_captures: int = REPEATABLE_CAPTURE_THRESHOLD,
) -> HMAAAttestationReport:
    if required_distinct_captures < 2:
        raise ValueError("repeatability threshold must be at least 2 captures")

    references = [_capture_reference(capture) for capture in captures]
    if not references:
        return HMAAAttestationReport(
            state=HMAAAttestationState.NO_EVIDENCE,
            blocking_reasons=["no qualifying capture evidence supplied"],
            claimable_labels=["IMPLEMENTED IN SOFTWARE", "REQUIRES PARTNER VALIDATION"],
        )

    mission_ids = {reference.mission_id for reference in references}
    if len(mission_ids) != 1:
        raise ValueError("all attested captures must use the same mission_id")
    mission_id = next(iter(mission_ids))

    distinct_hashes = sorted({reference.capture_sha256 for reference in references})
    repeatable = len(distinct_hashes) >= required_distinct_captures
    state = (
        HMAAAttestationState.EXTERNAL_ATTESTATION_REQUIRED
        if repeatable
        else HMAAAttestationState.CANDIDATE_EVIDENCE
    )
    blockers: list[str] = []
    if not repeatable:
        blockers.append(
            f"requires {required_distinct_captures} distinct qualifying captures; "
            f"found {len(distinct_hashes)}"
        )
    blockers.append(
        "independent external/partner attestation is required before any live-validation claim"
    )

    aggregate = _sha256_json(
        {
            "attestation_version": HMAA_ATTESTATION_VERSION,
            "mission_id": mission_id,
            "distinct_capture_sha256": distinct_hashes,
        }
    )
    ordered = sorted(references, key=lambda item: item.capture_sha256)
    return HMAAAttestationReport(
        mission_id=mission_id,
        state=state,
        capture_count=len(references),
        distinct_capture_count=len(distinct_hashes),
        repeatability_satisfied=repeatable,
        aggregate_sha256=aggregate,
        live_environment_validated=False,
        external_attestation_required=True,
        claimable_labels=["IMPLEMENTED IN SOFTWARE", "REQUIRES PARTNER VALIDATION"],
        blocking_reasons=blockers,
        captures=ordered,
    )
