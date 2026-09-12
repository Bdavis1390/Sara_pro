from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from worldshepherd_sara.echo_domain_evidence_bridge import (
    BRIDGE_EVENT,
    CLAIMS_BOUNDARY,
    DomainEvidenceEnvelope,
    ingest_domain_evidence,
)
from worldshepherd_sara.echo_event_store import EchoEventConflict, EchoEventStore, semantic_sha256
from worldshepherd_sara.evidence_artifacts import ArtifactRole


ARMY_HASH = "1" * 64
APNT_HASH = "2" * 64


def _army_envelope(**updates):
    payload = {
        "program_id": "WS-ADM-DEMO-001",
        "version": 1,
        "recommended_option_id": "OPTION-A",
        "package_state": "READY_FOR_HUMAN_REVIEW",
        "human_signoff": False,
    }
    values = {
        "domain": "ARMY_DECISION",
        "source_kind": "DecisionPackage",
        "source_id": "WS-ADM-DEMO-001:v1",
        "source_sha256": ARMY_HASH,
        "claim_state": "SIMULATED_ONLY",
        "claims_boundary": "Synthetic decision-program evidence only; no Army acceptance or acquisition authority.",
        "payload": payload,
        "parent_refs": (),
        "human_signoff": False,
        "execution_attempted": False,
    }
    values.update(updates)
    return DomainEvidenceEnvelope(**values)


def _apnt_envelope(**updates):
    values = {
        "domain": "APNT_AWARENESS",
        "source_kind": "APNTReplayResult",
        "source_id": "WS-NP004-POC-A-001:replay-1",
        "source_sha256": f"sha256:{APNT_HASH}",
        "claim_state": "SIMULATED_ONLY",
        "claims_boundary": "Synthetic informational-awareness replay only; no PNT-engine capability or action routing.",
        "payload": {
            "scenario_id": "WS-NP004-POC-A-001",
            "final_integrity_state": "RESTORED",
            "trace_complete": True,
            "execution_attempted": False,
        },
        "parent_refs": ("synthetic-fixture:v1",),
        "human_signoff": False,
        "execution_attempted": False,
    }
    values.update(updates)
    return DomainEvidenceEnvelope(**values)


def test_bridge_preserves_source_claims_and_never_marks_execution():
    envelope = _army_envelope()
    record = envelope.to_audit_record()

    assert record.event == BRIDGE_EVENT
    assert record.payload["claim_state"] == "SIMULATED_ONLY"
    assert record.payload["claims_boundary"] == envelope.claims_boundary
    assert record.payload["bridge_claims_boundary"] == CLAIMS_BOUNDARY
    assert record.payload["human_signoff"] is False
    assert record.payload["execution_attempted"] is False
    assert record.payload["source_sha256"] == f"sha256:{ARMY_HASH}"
    assert record.payload["_delivery_semantics"] == "AT_LEAST_ONCE"


def test_identical_replay_deduplicates_in_existing_echo_store(tmp_path):
    store = EchoEventStore(tmp_path.resolve())
    envelope = _apnt_envelope()

    first = ingest_domain_evidence(store, envelope)
    second = ingest_domain_evidence(store, envelope)

    assert first.outcome == "STORED"
    assert second.outcome == "DEDUPLICATED"
    assert first.record.event_id == second.record.event_id == envelope.stable_event_id()
    assert first.record.semantic_sha256 == semantic_sha256(envelope.to_audit_record())
    assert second.record.delivery_count == 2


def test_same_source_identity_with_changed_semantics_conflicts(tmp_path):
    store = EchoEventStore(tmp_path.resolve())
    original = _army_envelope()
    changed = _army_envelope(
        claims_boundary="Changed claim boundary must conflict under the same source identity.",
    )

    ingest_domain_evidence(store, original)
    assert changed.stable_event_id() == original.stable_event_id()
    with pytest.raises(EchoEventConflict, match="different semantic content"):
        ingest_domain_evidence(store, changed)


def test_bridge_payload_digest_changes_when_domain_payload_changes():
    original = _army_envelope()
    changed_payload = dict(original.payload)
    changed_payload["recommended_option_id"] = "OPTION-B"
    changed = _army_envelope(payload=changed_payload)

    assert changed.stable_event_id() == original.stable_event_id()
    assert changed.bridge_payload_sha256() != original.bridge_payload_sha256()


def test_execution_bearing_envelope_is_rejected_fail_closed():
    with pytest.raises(ValidationError, match="execution_attempted must be false"):
        _apnt_envelope(execution_attempted=True)


def test_non_finite_nested_payload_is_rejected():
    for value in (math.nan, math.inf, -math.inf):
        # Either the shared repository resource guard or this bridge's canonical
        # JSON guard may reject first. The contract is rejection, not a specific
        # error-string implementation detail.
        with pytest.raises(ValidationError):
            _army_envelope(payload={"metric": {"value": value}})


def test_duplicate_parent_refs_are_rejected():
    with pytest.raises(ValidationError, match="parent_refs must be unique"):
        _apnt_envelope(parent_refs=("same", "same"))


def test_artifact_evidence_uses_existing_evidence_contract():
    envelope = _apnt_envelope()
    artifact = envelope.to_artifact_evidence(locator="echo://domain/APNT_AWARENESS/WS-NP004-POC-A-001")

    assert artifact.role == ArtifactRole.SOURCE
    assert artifact.sha256.startswith("sha256:")
    assert artifact.media_type == "application/json"


def test_event_identity_is_source_identity_not_mutable_payload():
    original = _apnt_envelope()
    altered = _apnt_envelope(payload={"scenario_id": "WS-NP004-POC-A-001", "trace_complete": False})

    assert altered.stable_event_id() == original.stable_event_id()
    assert altered.bridge_payload_sha256() != original.bridge_payload_sha256()
