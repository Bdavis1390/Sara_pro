from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from worldshepherd_sara.event_outbox import drain_event_outbox
from worldshepherd_sara.qcrypto_audit_adapter import (
    new_qcrypto_audit_instance_id,
    qcrypto_decision_digest,
    qcrypto_outbox_events,
    queue_qcrypto_projection_patch,
)
from worldshepherd_sara.qcrypto_audit_verifier import verify_qcrypto_audit_chain
from worldshepherd_sara.qcrypto_prime_review_adapter import (
    QCryptoPrimeReviewAdapterError,
    prime_governed_review_outbox_events,
    prime_governed_review_projection,
)
from worldshepherd_sara.storage import DurableStore


def _digest(value) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return sha256(canonical).hexdigest()


def review_evidence():
    prime_digest = "a" * 64
    governed_digest = "b" * 64
    negotiated_digest = "c" * 64
    transcript_digest = "d" * 64
    binding = {
        "schema": "WS-QCRYPTO-PRIME-GOVERNED-RELEASE-REVIEW-V1",
        "prime_evidence_sha256": prime_digest,
        "governed_evidence_sha256": governed_digest,
        "prime_signing_algorithm": "ML-DSA-65",
        "prime_signature_context": "WS-PRIME-SENTINEL-AUTHZ-V2",
        "prime_activation_disposition": "ACTIVATION_ALLOWED",
        "prime_authorization_registry_status": "CONSUMED",
        "governed_terminal_state": "HUMAN_REVIEW_REQUIRED",
        "governed_selected_suite_id": "HYBRID-ECDSA-MLDSA",
        "governed_pq_algorithm_id": "ML-DSA",
        "governed_negotiated_context_digest": negotiated_digest,
        "governed_negotiation_transcript_digest": transcript_digest,
        "human_release_required": True,
        "execution_authority": False,
        "live_value_authorized": False,
    }
    review_digest = _digest(binding)
    decision = {
        "verdict": "PRIME_GOVERNED_RELEASE_READY_FOR_HUMAN_REVIEW",
        "ready_for_human_release_review": True,
        "blockers": [],
        "warnings": ["bounded activation is not execution authority"],
        "prime_evidence_sha256": prime_digest,
        "governed_evidence_sha256": governed_digest,
        "review_package_sha256": review_digest,
        "prime_signing_algorithm": "ML-DSA-65",
        "prime_signature_context": "WS-PRIME-SENTINEL-AUTHZ-V2",
        "prime_activation_disposition": "ACTIVATION_ALLOWED",
        "prime_authorization_registry_status": "CONSUMED",
        "governed_terminal_state": "HUMAN_REVIEW_REQUIRED",
        "governed_selected_suite_id": "HYBRID-ECDSA-MLDSA",
        "governed_pq_algorithm_id": "ML-DSA",
        "governed_negotiated_context_digest": negotiated_digest,
        "governed_negotiation_transcript_digest": transcript_digest,
        "human_release_required": True,
        "human_release_recorded": False,
        "execution_authority": False,
        "live_value_authorized": False,
        "live_transaction_signed": False,
        "production_protocol_integration": False,
        "end_to_end_pq_security_established": False,
        "claim_boundary": "human review only",
    }
    summary = {
        "ready_for_human_release_review": True,
        "human_release_required": True,
        "human_release_recorded": False,
        "prime_signing_algorithm": "ML-DSA-65",
        "prime_signature_context": "WS-PRIME-SENTINEL-AUTHZ-V2",
        "prime_activation_disposition": "ACTIVATION_ALLOWED",
        "prime_authorization_registry_status": "CONSUMED",
        "governed_terminal_state": "HUMAN_REVIEW_REQUIRED",
        "governed_selected_suite_id": "HYBRID-ECDSA-MLDSA",
        "governed_pq_algorithm_id": "ML-DSA",
        "review_package_sha256": review_digest,
        "execution_authority": False,
        "live_value_authorized": False,
        "live_transaction_signed": False,
        "production_protocol_integration": False,
        "end_to_end_pq_security_established": False,
    }
    evidence = {
        "schema": "WS-QCRYPTO-PRIME-GOVERNED-RELEASE-REVIEW-V1",
        "status": "PASS",
        "claim_state": "PRIME_AND_QCRYPTO_EVIDENCE_BOUND_FOR_HUMAN_REVIEW_ONLY",
        "proof_scope": "CROSS_BOUNDARY_REVIEW_PACKAGE_NO_EXECUTION_AUTHORITY",
        "decision": decision,
        "source_evidence": {
            "prime_evidence_sha256": prime_digest,
            "governed_evidence_sha256": governed_digest,
        },
        "summary": summary,
    }
    evidence["evidence_sha256"] = _digest(evidence)
    return evidence


def _refresh_outer_digest(evidence):
    evidence = deepcopy(evidence)
    evidence.pop("evidence_sha256", None)
    evidence["evidence_sha256"] = _digest(evidence)
    return evidence


def test_review_warrant_maps_to_existing_native_qcrypto_projection():
    evidence = review_evidence()
    projection = prime_governed_review_projection(evidence)
    review_digest = evidence["summary"]["review_package_sha256"]
    assert projection["asset_id"] == f"PRIME-QCRYPTO-REVIEW:{review_digest}"
    assert projection["correlation_id"] == f"sha256:{review_digest}"
    assert projection["echo_state"] == "CROSS_BOUNDARY_REVIEW_EVIDENCE_READY"
    assert projection["prime_state"] == "MLDSA65_AUTHORIZATION_EVIDENCE_CONSUMED"
    assert projection["sara_state"] == "HUMAN_RELEASE_REVIEW_REQUIRED"
    assert projection["overwatch_state"] == "REVIEW_PACKAGE_MONITOR_ONLY"
    assert projection["human_approval_required"] is True
    assert projection["migration_executed"] is False
    assert projection["execution_authority"] is False
    assert projection["live_value_authorized"] is False
    assert projection["federal_compliance_established"] is False
    assert projection["ws_cae_conformance_established"] is False


def test_review_warrant_uses_exact_existing_four_event_contract():
    evidence = review_evidence()
    events = prime_governed_review_outbox_events(evidence, actor="SSPADAWANZZ")
    assert [event["event"] for event in events] == [
        "qcrypto_echo_state",
        "qcrypto_prime_state",
        "qcrypto_sara_state",
        "qcrypto_overwatch_state",
    ]
    assert [event["payload"]["stage"] for event in events] == [
        "ECHO",
        "PRIME",
        "SARA",
        "OVERWATCH",
    ]
    for event in events:
        payload = event["payload"]
        assert payload["human_approval_required"] is True
        assert payload["migration_executed"] is False
        assert payload["execution_authority"] is False
        assert payload["live_value_authorized"] is False
        assert payload["federal_compliance_established"] is False
        assert payload["ws_cae_conformance_established"] is False


def test_review_warrant_persists_and_reconstructs_through_native_sara_audit(tmp_path):
    evidence = review_evidence()
    projection = prime_governed_review_projection(evidence)
    decision_digest = qcrypto_decision_digest(projection)
    audit_instance_id = new_qcrypto_audit_instance_id()
    store = DurableStore(tmp_path / "data")

    def operation(registry):
        patch, ids = queue_qcrypto_projection_patch(
            registry,
            projection,
            actor="SSPADAWANZZ",
            audit_instance_id=audit_instance_id,
        )
        return patch, ids

    event_ids = store.transact_registry(operation)
    assert len(event_ids) == 4
    assert drain_event_outbox(store, limit=4) == 4
    records = [
        item
        for item in store.read_audit(100)
        if str(item.get("event", "")).startswith("qcrypto_")
    ]
    verification = verify_qcrypto_audit_chain(
        records,
        decision_digest=decision_digest,
        audit_instance_id=audit_instance_id,
    )
    assert verification.verdict == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert verification.complete is True
    assert verification.consistent is True
    assert verification.stages_present == ("ECHO", "PRIME", "SARA", "OVERWATCH")
    assert verification.missing_stages == ()
    assert verification.logical_event_count == 4
    assert verification.execution_authority is False
    assert verification.live_value_authorized is False
    assert verification.federal_compliance_established is False
    assert verification.ws_cae_conformance_established is False


def test_projection_and_semantic_decision_digest_are_deterministic():
    first = prime_governed_review_projection(review_evidence())
    second = prime_governed_review_projection(review_evidence())
    assert first == second
    assert qcrypto_decision_digest(first) == qcrypto_decision_digest(second)


def test_outer_wrapper_tamper_is_rejected_before_audit_projection():
    evidence = review_evidence()
    evidence["summary"]["prime_authorization_registry_status"] = "VERIFIED"
    with pytest.raises(QCryptoPrimeReviewAdapterError, match="wrapper digest"):
        prime_governed_review_projection(evidence)


def test_inner_review_digest_must_reconstruct_even_if_outer_digest_is_refreshed():
    evidence = review_evidence()
    forged = "f" * 64
    evidence["decision"]["review_package_sha256"] = forged
    evidence["summary"]["review_package_sha256"] = forged
    evidence = _refresh_outer_digest(evidence)
    with pytest.raises(QCryptoPrimeReviewAdapterError, match="does not reconstruct"):
        prime_governed_review_projection(evidence)


def test_negotiated_context_tamper_is_rejected_even_with_refreshed_outer_digest():
    evidence = review_evidence()
    evidence["decision"]["governed_negotiated_context_digest"] = "e" * 64
    evidence = _refresh_outer_digest(evidence)
    with pytest.raises(QCryptoPrimeReviewAdapterError, match="does not reconstruct"):
        prime_governed_review_projection(evidence)


@pytest.mark.parametrize(
    "field",
    [
        "execution_authority",
        "live_value_authorized",
        "live_transaction_signed",
        "production_protocol_integration",
        "end_to_end_pq_security_established",
    ],
)
def test_authority_or_scope_promotion_is_rejected(field):
    evidence = review_evidence()
    evidence["decision"][field] = True
    evidence["summary"][field] = True
    evidence = _refresh_outer_digest(evidence)
    with pytest.raises(QCryptoPrimeReviewAdapterError, match=field):
        prime_governed_review_projection(evidence)


def test_pre_recorded_human_release_is_rejected():
    evidence = review_evidence()
    evidence["decision"]["human_release_recorded"] = True
    evidence["summary"]["human_release_recorded"] = True
    evidence = _refresh_outer_digest(evidence)
    with pytest.raises(QCryptoPrimeReviewAdapterError, match="pre-record"):
        prime_governed_review_projection(evidence)
