from __future__ import annotations

import json

from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.improvement_runtime import ImprovementRuntime, ImprovementRuntimeError
from worldshepherd_sara.models import AuditRecord


def operational_signal(event_id: str) -> AuditRecord:
    return AuditRecord(
        timestamp="2026-09-12T20:00:00+00:00",
        event="wsri_operational_signal",
        actor="OVERWATCH",
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "_ws_improvement_signal": {
                "source": "OVERWATCH",
                "trigger_kind": "OPERATOR_FEEDBACK",
                "statement": "evaluate the recorded operational improvement input",
                "affected_lanes": ["OVERWATCH", "WS-RI"],
                "required_tests": ["source-gate"],
                "success_metrics": ["required validation passes"],
                "risk_level": "MODERATE",
            },
        },
    )


def test_runtime_cursor_survives_restart(tmp_path):
    wsri = (tmp_path / "wsri").resolve()
    echo_dir = (tmp_path / "echo").resolve()
    echo_dir.mkdir(mode=0o700)
    echo = EchoEventStore(echo_dir)
    echo.ingest(operational_signal("SARA-EVENT-runtime-0001"))

    runtime = ImprovementRuntime(wsri, echo_data_dir=echo_dir)
    report = runtime.run_feedback_once(actor="admin")
    assert report.proposals_stored == 1
    assert report.claim_promotion_performed is False
    assert report.deployment_performed is False

    cursor = runtime.load_cursor()
    restarted = ImprovementRuntime(wsri, echo_data_dir=echo_dir)
    assert restarted.load_cursor() == cursor
    assert restarted.status()["ledger_chain_verified"] is True
    assert restarted.status()["record_count"] == 1
    assert restarted.status()["feedback_cursor_digest"]


def test_runtime_checkpoint_payload_preserves_claims_boundary(tmp_path):
    wsri = (tmp_path / "wsri").resolve()
    echo_dir = (tmp_path / "echo").resolve()
    echo_dir.mkdir(mode=0o700)
    echo = EchoEventStore(echo_dir)
    echo.ingest(operational_signal("SARA-EVENT-runtime-0002"))
    runtime = ImprovementRuntime(wsri, echo_data_dir=echo_dir)
    runtime.run_feedback_once(actor="admin")

    payload = runtime.checkpoint_outbox_payload(created_utc="2026-09-12T20:05:00+00:00")
    assert payload["anchor_schema"] == "WS-RI-LEDGER-ECHO-ANCHOR-V1"
    assert "signed inclusion require" in payload["claims_boundary"]
    records = runtime.export_records(limit=1)
    assert records[0]["state"] == "PROPOSED"


def test_runtime_requires_echo_source_for_feedback(tmp_path):
    runtime = ImprovementRuntime((tmp_path / "wsri").resolve())
    try:
        runtime.run_feedback_once(actor="admin")
    except ImprovementRuntimeError as exc:
        assert "ECHO source" in str(exc)
    else:
        raise AssertionError("feedback must require configured ECHO source")


def test_runtime_rejects_tampered_cursor_state(tmp_path):
    wsri = (tmp_path / "wsri").resolve()
    echo_dir = (tmp_path / "echo").resolve()
    echo_dir.mkdir(mode=0o700)
    echo = EchoEventStore(echo_dir)
    echo.ingest(operational_signal("SARA-EVENT-runtime-0003"))
    runtime = ImprovementRuntime(wsri, echo_data_dir=echo_dir)
    runtime.run_feedback_once(actor="admin")

    state = json.loads(runtime.state_path.read_text(encoding="utf-8"))
    state["feedback_cursor"]["cycle_index"] += 1
    runtime.state_path.write_text(json.dumps(state), encoding="utf-8")

    try:
        runtime.load_cursor()
    except ImprovementRuntimeError as exc:
        assert "digest mismatch" in str(exc)
    else:
        raise AssertionError("tampered cursor state must be rejected")
