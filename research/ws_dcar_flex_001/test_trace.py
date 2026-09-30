import json
from pathlib import Path

import pytest

from model import FlexRequest, Verdict
from replay import replay_payload
from trace import TracePoint, verify_trace


FIXTURE = Path(__file__).with_name("fixtures") / "flex_001_trace.json"


def load_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def build(payload: dict) -> tuple[FlexRequest, list[TracePoint]]:
    request = FlexRequest(**payload["request"])
    points = [TracePoint(**point) for point in payload["points"]]
    return request, points


def test_trace_fixture_verifies():
    payload = load_payload()
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.VERIFIED.value
    assert result["response_latency_s"] == pytest.approx(180.0)
    assert result["maintained_duration_s"] == pytest.approx(1800.0)
    assert result["source_mismatch_mwh"] == pytest.approx(0.0)


def test_replay_preserves_provenance_and_hashes_input():
    payload = load_payload()
    result = replay_payload(payload)
    assert result["provenance"] == payload["provenance"]
    assert len(result["input_sha256"]) == 64
    assert len(result["trace_sha256"]) == 64
    assert result["input_sha256"] != result["trace_sha256"]


def test_replay_hash_changes_when_trace_changes():
    payload = load_payload()
    original = replay_payload(payload)
    payload["points"][3]["grid_import_mw"] = 79.75
    changed = replay_payload(payload)
    assert changed["input_sha256"] != original["input_sha256"]
    assert changed["trace_sha256"] != original["trace_sha256"]


def test_trace_detects_configuration_drift():
    payload = load_payload()
    payload["points"][5]["configuration_id"] = "cfg-unrecorded-change"
    request, points = build(payload)
    result = verify_trace(request, payload["baseline_mw"], points)
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert "configuration_drift_detected" in result.reasons


def test_trace_detects_meter_identity_change():
    payload = load_payload()
    payload["points"][4]["meter_id"] = "grid-meter-shadow"
    request, points = build(payload)
    result = verify_trace(request, payload["baseline_mw"], points)
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert "meter_identity_changed" in result.reasons


def test_trace_detects_excessive_telemetry_gap():
    payload = load_payload()
    del payload["points"][4:6]
    request, points = build(payload)
    result = verify_trace(
        request,
        payload["baseline_mw"],
        points,
        max_gap_s=300.0,
    )
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert "telemetry_gap_exceeded" in result.reasons


def test_trace_rejects_unauthorized_success():
    payload = load_payload()
    request, points = build(payload)
    result = verify_trace(
        request,
        payload["baseline_mw"],
        points,
        authorized=False,
    )
    assert result.verdict is Verdict.NONCOMPLIANT
    assert "unauthorized_control_action" in result.reasons


def test_trace_detects_late_response():
    payload = load_payload()
    for point in payload["points"][1:3]:
        point["grid_import_mw"] = 85.0
        point["workload_pause_mw"] = 6.0
        point["workload_migration_mw"] = 3.0
        point["battery_discharge_mw"] = 4.0
        point["hvac_reduction_mw"] = 2.0
    request, points = build(payload)
    result = verify_trace(request, payload["baseline_mw"], points)
    assert result.verdict is Verdict.NONCOMPLIANT
    assert "response_deadline_missed" in result.reasons


def test_trace_detects_duration_shortfall():
    payload = load_payload()
    payload["points"][-1]["grid_import_mw"] = 83.0
    request, points = build(payload)
    result = verify_trace(request, payload["baseline_mw"], points)
    assert result.verdict is Verdict.NONCOMPLIANT
    assert "minimum_duration_not_met" in result.reasons


def test_trace_surfaces_generator_substitution():
    payload = load_payload()
    for point in payload["points"][2:]:
        point["battery_discharge_mw"] = 2.0
        point["onsite_generation_mw"] = 3.0
    request, points = build(payload)
    result = verify_trace(request, payload["baseline_mw"], points)
    assert result.verdict is Verdict.VERIFIED_WITH_EXCEPTIONS
    assert "onsite_generation_substitution" in result.reasons


def test_trace_surfaces_energy_decomposition_mismatch():
    payload = load_payload()
    for point in payload["points"][2:]:
        point["battery_discharge_mw"] = 1.0
    request, points = build(payload)
    result = verify_trace(request, payload["baseline_mw"], points)
    assert result.verdict is Verdict.VERIFIED_WITH_EXCEPTIONS
    assert "energy_decomposition_mismatch" in result.reasons
    assert result.source_mismatch_mwh > 0.25


def test_trace_rejects_stale_telemetry():
    payload = load_payload()
    payload["points"][3]["telemetry_fresh"] = False
    request, points = build(payload)
    result = verify_trace(request, payload["baseline_mw"], points)
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert "stale_telemetry" in result.reasons
