from __future__ import annotations

from pydantic import ValidationError

from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.improvement_evidence_export import (
    build_evidence_manifest,
    manifest_matches_runtime,
    verify_evidence_manifest,
)
from worldshepherd_sara.improvement_feedback import ImprovementFeedbackPolicy
from worldshepherd_sara.improvement_handoff import (
    ImprovementSchedulerHandoff,
    build_scheduler_handoff,
    verify_scheduler_handoff,
)
from worldshepherd_sara.improvement_runtime import ImprovementRuntime, ImprovementRuntimeError
from worldshepherd_sara.models import AuditRecord


def signal(event_id: str) -> AuditRecord:
    return AuditRecord(
        timestamp="2026-09-12T21:00:00+00:00",
        event="wsri_operational_signal",
        actor="OVERWATCH",
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "_ws_improvement_signal": {
                "source": "OVERWATCH",
                "trigger_kind": "OPERATOR_FEEDBACK",
                "statement": "evaluate bounded operational evidence",
                "affected_lanes": ["OVERWATCH"],
                "required_tests": ["source-gate"],
                "success_metrics": ["required validation passes"],
                "risk_level": "MODERATE",
            },
        },
    )


def seeded_runtime(tmp_path) -> ImprovementRuntime:
    wsri = (tmp_path / "wsri").resolve()
    echo_dir = (tmp_path / "echo").resolve()
    echo_dir.mkdir(mode=0o700)
    echo = EchoEventStore(echo_dir)
    echo.ingest(signal("SARA-EVENT-handoff-0001"))
    runtime = ImprovementRuntime(wsri, echo_data_dir=echo_dir)
    runtime.run_feedback_once(actor="operator")
    return runtime


def test_scheduler_handoff_is_verifiable_and_never_self_authorizes(tmp_path):
    runtime = seeded_runtime(tmp_path)
    handoff = build_scheduler_handoff(
        runtime,
        requested_by="operator",
        generated_utc="2026-09-12T21:05:00+00:00",
        policy=ImprovementFeedbackPolicy(
            max_echo_events_per_cycle=8,
            max_new_proposals_per_cycle=4,
        ),
    )
    assert verify_scheduler_handoff(handoff) is True
    assert handoff.execution_disposition.value == "HUMAN_REVIEW_REQUIRED"
    assert handoff.authorization_required is True
    assert handoff.autonomous_execution_authorized is False
    assert handoff.claim_promotion_authorized is False
    assert handoff.deployment_authorized is False
    assert handoff.external_execution_authorized is False


def test_scheduler_handoff_rejects_authority_escalation(tmp_path):
    runtime = seeded_runtime(tmp_path)
    handoff = build_scheduler_handoff(
        runtime,
        requested_by="operator",
        generated_utc="2026-09-12T21:05:00+00:00",
    )
    data = handoff.model_dump(mode="json")
    data["deployment_authorized"] = True
    try:
        ImprovementSchedulerHandoff.model_validate(data)
    except ValidationError:
        pass
    else:
        raise AssertionError("handoff must reject deployment authority")


def test_scheduler_handoff_requires_echo_source(tmp_path):
    runtime = ImprovementRuntime((tmp_path / "wsri").resolve())
    try:
        build_scheduler_handoff(
            runtime,
            requested_by="operator",
            generated_utc="2026-09-12T21:05:00+00:00",
        )
    except ImprovementRuntimeError as exc:
        assert "ECHO source" in str(exc)
    else:
        raise AssertionError("feedback handoff must require ECHO source")


def test_evidence_manifest_verifies_and_matches_runtime(tmp_path):
    runtime = seeded_runtime(tmp_path)
    manifest = build_evidence_manifest(
        runtime,
        generated_utc="2026-09-12T21:06:00+00:00",
    )
    assert verify_evidence_manifest(manifest) is True
    assert manifest_matches_runtime(manifest, runtime) is True
    assert manifest.record_count == 1
    assert manifest.ledger_chain_verified is True
    assert manifest.claim_promotion_performed is False
    assert manifest.deployment_performed is False


def test_manifest_detects_tampering_and_runtime_drift(tmp_path):
    runtime = seeded_runtime(tmp_path)
    manifest = build_evidence_manifest(
        runtime,
        generated_utc="2026-09-12T21:06:00+00:00",
    )
    tampered = manifest.model_copy(update={"record_count": 999})
    assert verify_evidence_manifest(tampered) is False

    echo = runtime.echo_store
    assert echo is not None
    echo.ingest(signal("SARA-EVENT-handoff-0002"))
    runtime.run_feedback_once(actor="operator")
    assert manifest_matches_runtime(manifest, runtime) is False


def test_empty_runtime_can_emit_evidence_manifest(tmp_path):
    runtime = ImprovementRuntime((tmp_path / "wsri").resolve())
    manifest = build_evidence_manifest(
        runtime,
        generated_utc="2026-09-12T21:06:00+00:00",
    )
    assert manifest.record_count == 0
    assert manifest.head_record_digest is None
    assert verify_evidence_manifest(manifest) is True
