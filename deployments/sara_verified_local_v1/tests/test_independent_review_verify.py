from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierSafetyPolicy,
    evaluate_frontier_action,
)
from worldshepherd_sara.fasa_admission_evidence import build_admission_evidence
from worldshepherd_sara.fasa_runtime_gate import (
    FASAEchoExecutionReadiness,
    FASAExecutionReadinessConsumption,
)
from worldshepherd_sara.independent_checkpoint_corroboration import (
    corroborate_overwatch_checkpoint,
)
from worldshepherd_sara.independent_evaluator import build_independent_evaluator_report
from worldshepherd_sara.independent_review_export import (
    build_independent_review_export_bundle,
)
from worldshepherd_sara.independent_review_package import build_independent_review_package
from worldshepherd_sara.independent_review_verify import (
    verify_serialized_independent_review_export,
)
import worldshepherd_sara.independent_review_verify as verify_module
from worldshepherd_sara.overwatch_attestation_contract import OverwatchAttestationContract
from worldshepherd_sara.overwatch_provenance import deliver_overwatch_intent_provenance
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 15, 30, tzinfo=timezone.utc)


def _serialized_valid_bundle(tmp_path, echo_checkpoint_key) -> str:
    key, _path = echo_checkpoint_key
    action_id = "ACTION-SERIALIZED-REVIEW"
    model_id = "MODEL-SERIALIZED-REVIEW"
    model_version = "v1"

    candidate = FrontierActionCandidate(
        action_id=action_id,
        model_id=model_id,
        model_version=model_version,
        capability_level=CapabilityLevel.F1,
        reversible=True,
        consequential_external_effect=False,
    )
    registry = CapabilityRegistryEntry(
        model_id=model_id,
        model_version=model_version,
        assessed_level=CapabilityLevel.F1,
        maximum_authorized_level=CapabilityLevel.F1,
        evaluation_id="EVAL-SERIALIZED-REVIEW",
        evaluation_current=True,
    )
    policy = FrontierSafetyPolicy(policy_id="POLICY-SERIALIZED-REVIEW")
    disposition, reasons = evaluate_frontier_action(candidate, registry, policy)
    admission = build_admission_evidence(
        candidate,
        registry,
        policy,
        disposition,
        reasons,
        assessed_at=NOW,
    )

    observation = OverwatchObservation(
        observation_id="OBS-SERIALIZED-REVIEW",
        action_id=action_id,
        monitor_id="OVERWATCH-SERIALIZED-REVIEW",
        model_id=model_id,
        model_version=model_version,
        observed_at=NOW + timedelta(seconds=1),
        telemetry_complete=True,
        monitor_heartbeat_present=True,
        signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    )
    attestation = OverwatchAttestationContract(
        attestation_id="ATTEST-SERIALIZED-REVIEW",
        observation=observation,
        issued_at=NOW + timedelta(seconds=2),
        expires_at=NOW + timedelta(seconds=12),
        nonce="nonce-serialized-review-0001",
    )

    sara = DurableStore(tmp_path / "sara-serialized-review")
    echo = EchoEventStore((tmp_path / "echo-serialized-review").resolve())
    decision = classify_overwatch_observation(observation)
    intent = record_overwatch_containment_intent(
        sara,
        decision=decision,
        now=NOW + timedelta(seconds=3),
    )
    receipt = deliver_overwatch_intent_provenance(
        sara,
        echo,
        intent=intent,
    )

    manager = EchoCheckpointManager(
        echo,
        private_key=key,
        key_id="ECHO-CHECKPOINT-SERIALIZED-REVIEW-V1",
    )
    checkpoint = manager.create_checkpoint()
    corroboration = corroborate_overwatch_checkpoint(
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        checkpoint_bundle=checkpoint,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    report = build_independent_evaluator_report(
        review_id="INDEPENDENT-SERIALIZED-REVIEW",
        admission_evidence=admission,
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        evaluated_at=NOW + timedelta(seconds=20),
    )
    package = build_independent_review_package(
        evaluator_report=report,
        checkpoint_corroboration=corroboration,
    )
    export = build_independent_review_export_bundle(
        review_package=package,
        evaluator_report=report,
        checkpoint_corroboration=corroboration,
        admission_evidence=admission,
        overwatch_attestation=attestation,
        overwatch_provenance=receipt,
        checkpoint_bundle=checkpoint,
        expected_checkpoint_key_fingerprint_sha256=manager.fingerprint_sha256,
    )
    return export.model_dump_json()


@pytest.mark.parametrize("as_bytes", [False, True])
def test_serialized_verifier_passes_valid_reproducible_bundle(
    tmp_path,
    echo_checkpoint_key,
    as_bytes,
):
    serialized = _serialized_valid_bundle(tmp_path, echo_checkpoint_key)
    supplied = serialized.encode("utf-8") if as_bytes else serialized
    result = verify_serialized_independent_review_export(supplied)

    assert result.status == "PASS"
    assert result.code == "VERIFIED"
    assert result.bundle_digest_sha256 is not None
    assert result.verification_scope == "LOCAL_EVIDENCE_REPRODUCTION_ONLY"
    assert result.monitor_verification_status == "UNVERIFIED"
    assert result.approval_status == "NOT_APPROVED_BY_THIS_RESULT"
    assert result.authorization_effect == "NONE"
    assert result.readiness_effect == "NONE"
    assert result.execution_effect_applied is False


def test_serialized_verifier_rejects_duplicate_keys_before_schema_validation():
    result = verify_serialized_independent_review_export(
        '{"schema":"first","schema":"second"}'
    )
    assert result.status == "FAIL"
    assert result.code == "DUPLICATE_JSON_KEY"
    assert "schema" in result.detail


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_serialized_verifier_rejects_non_standard_json_constants(constant):
    result = verify_serialized_independent_review_export(f'{{"value":{constant}}}')
    assert result.status == "FAIL"
    assert result.code == "INVALID_JSON"
    assert constant in result.detail


def test_serialized_verifier_rejects_invalid_utf8():
    result = verify_serialized_independent_review_export(b"\xff\xfe")
    assert result.status == "FAIL"
    assert result.code == "INVALID_UTF8"


def test_serialized_verifier_rejects_malformed_json():
    result = verify_serialized_independent_review_export('{"schema":')
    assert result.status == "FAIL"
    assert result.code == "INVALID_JSON"


def test_serialized_verifier_rejects_non_object_top_level():
    result = verify_serialized_independent_review_export("[]")
    assert result.status == "FAIL"
    assert result.code == "TOP_LEVEL_NOT_OBJECT"


def test_serialized_verifier_rejects_unknown_schema_field(
    tmp_path,
    echo_checkpoint_key,
):
    payload = json.loads(_serialized_valid_bundle(tmp_path, echo_checkpoint_key))
    payload["unexpected_field"] = "must fail closed"
    result = verify_serialized_independent_review_export(
        json.dumps(payload, separators=(",", ":"))
    )

    assert result.status == "FAIL"
    assert result.code == "SCHEMA_VALIDATION_FAILED"
    assert "unexpected_field" in result.detail


def test_serialized_verifier_replays_evidence_and_rejects_checkpoint_tamper(
    tmp_path,
    echo_checkpoint_key,
):
    payload = json.loads(_serialized_valid_bundle(tmp_path, echo_checkpoint_key))
    payload["checkpoint_bundle"]["signature_b64url"] = "tampered-signature"
    result = verify_serialized_independent_review_export(
        json.dumps(payload, separators=(",", ":"))
    )

    assert result.status == "FAIL"
    assert result.code == "EVIDENCE_VERIFICATION_FAILED"
    assert "checkpoint" in result.detail.lower()
    assert result.authorization_effect == "NONE"
    assert result.readiness_effect == "NONE"
    assert result.execution_effect_applied is False


def test_serialized_verifier_enforces_bounded_input(monkeypatch):
    monkeypatch.setattr(verify_module, "MAX_SERIALIZED_REVIEW_BUNDLE_BYTES", 16)
    result = verify_serialized_independent_review_export("x" * 17)
    assert result.status == "FAIL"
    assert result.code == "INPUT_TOO_LARGE"


def test_serialized_verifier_rejects_unsupported_input_type():
    result = verify_serialized_independent_review_export(123)  # type: ignore[arg-type]
    assert result.status == "FAIL"
    assert result.code == "UNSUPPORTED_INPUT_TYPE"


@pytest.mark.parametrize("valid", [True, False])
def test_verification_result_cannot_validate_as_readiness_or_consumption(
    tmp_path,
    echo_checkpoint_key,
    valid,
):
    if valid:
        serialized = _serialized_valid_bundle(tmp_path, echo_checkpoint_key)
    else:
        serialized = "{}"
    result = verify_serialized_independent_review_export(serialized)
    payload = result.model_dump(mode="json")

    with pytest.raises(ValidationError):
        FASAEchoExecutionReadiness.model_validate(payload)
    with pytest.raises(ValidationError):
        FASAExecutionReadinessConsumption.model_validate(payload)
