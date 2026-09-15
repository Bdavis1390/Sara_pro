from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field


ASSURANCE_EVIDENCE_SCHEMA = "WS-ASSURANCE-EVIDENCE-V1"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class AssuranceEvidenceBundle(BaseModel):
    schema: Literal[ASSURANCE_EVIDENCE_SCHEMA] = ASSURANCE_EVIDENCE_SCHEMA
    bundle_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    created_utc: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    readiness: Literal["READY", "DEGRADED"]
    degraded_metrics: list[str]
    baseline_digest: str = Field(pattern=_SHA256_PATTERN)
    active_configuration_digest: str = Field(pattern=_SHA256_PATTERN)
    authorization_state: str = Field(min_length=1, max_length=64)
    reviewer: str | None = Field(default=None, max_length=128)
    replay_event_digests: list[str]
    audit_record_digests: list[str]
    predecessor_manifest_digest: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    manifest_digest: str = Field(pattern=_SHA256_PATTERN)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _manifest_payload(bundle: AssuranceEvidenceBundle | dict[str, Any]) -> dict[str, Any]:
    if isinstance(bundle, AssuranceEvidenceBundle):
        payload = bundle.model_dump(mode="json")
    else:
        payload = dict(bundle)
    payload.pop("manifest_digest", None)
    return payload


def build_assurance_evidence_bundle(
    *,
    bundle_id: str,
    created_utc: str,
    source_ref: str,
    readiness: Literal["READY", "DEGRADED"],
    degraded_metrics: list[str],
    baseline_digest: str,
    active_configuration_digest: str,
    authorization_state: str,
    reviewer: str | None,
    replay_events: list[dict[str, Any]],
    audit_records: list[dict[str, Any]],
    predecessor_manifest_digest: str | None = None,
) -> AssuranceEvidenceBundle:
    payload: dict[str, Any] = {
        "schema": ASSURANCE_EVIDENCE_SCHEMA,
        "bundle_id": bundle_id,
        "created_utc": created_utc,
        "source_ref": source_ref,
        "readiness": readiness,
        "degraded_metrics": sorted(set(degraded_metrics)),
        "baseline_digest": baseline_digest,
        "active_configuration_digest": active_configuration_digest,
        "authorization_state": authorization_state,
        "reviewer": reviewer,
        "replay_event_digests": [_digest(event) for event in replay_events],
        "audit_record_digests": [_digest(record) for record in audit_records],
        "predecessor_manifest_digest": predecessor_manifest_digest,
    }
    payload["manifest_digest"] = _digest(payload)
    return AssuranceEvidenceBundle.model_validate(payload)


def verify_assurance_evidence_bundle(bundle: AssuranceEvidenceBundle) -> bool:
    expected = _digest(_manifest_payload(bundle))
    return expected == bundle.manifest_digest


def verify_assurance_evidence_chain(bundles: list[AssuranceEvidenceBundle]) -> bool:
    if not bundles:
        return True
    for index, bundle in enumerate(bundles):
        if not verify_assurance_evidence_bundle(bundle):
            return False
        expected_predecessor = None if index == 0 else bundles[index - 1].manifest_digest
        if bundle.predecessor_manifest_digest != expected_predecessor:
            return False
    return True
