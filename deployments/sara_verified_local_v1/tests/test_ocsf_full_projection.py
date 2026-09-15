from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.ocsf_full_projection import (
    OCSF_COMPILER_COMMIT,
    OCSF_SCHEMA_COMMIT,
    OCSF_TOOLKIT_COMMIT,
    OCSF_VERSION,
    build_full_ocsf_event,
)
from worldshepherd_sara.qualification import canonical_digest
from worldshepherd_sara.standards_interop import (
    ExpectedOutcome,
    InteropCaseDefinition,
    build_interop_fixture,
)


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "fixtures" / "standards_interop" / "corpus_v0_1.json"
LOCK_PATH = ROOT / "fixtures" / "standards_interop" / "corpus_v0_1.lock.json"


def _cases() -> list[InteropCaseDefinition]:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return [InteropCaseDefinition.model_validate(case) for case in corpus["cases"]]


def test_projection_is_pinned_to_exact_upstream_revisions():
    assert OCSF_SCHEMA_COMMIT == "c1ab05a382ffc97250997ffe010f3f715a097c2a"
    assert OCSF_COMPILER_COMMIT == "865887a9ee88580c471062f93da115e7599fa31d"
    assert OCSF_TOOLKIT_COMMIT == "a99619fcd148791a6a9fe5f82c1e0d839f658591"
    assert OCSF_VERSION == "1.10.0-dev"


def test_frozen_source_corpus_is_not_changed_by_projection():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    before = canonical_digest(corpus)
    for case in _cases():
        build_full_ocsf_event(case)
    after = canonical_digest(json.loads(CORPUS_PATH.read_text(encoding="utf-8")))
    assert before == lock["canonical_sha256"]
    assert after == before


def test_all_seven_cases_build_with_required_ocsf_base_fields_and_type_uid_formula():
    cases = _cases()
    assert len(cases) == 7
    required = {
        "activity_id",
        "category_uid",
        "class_uid",
        "metadata",
        "severity_id",
        "time",
        "type_uid",
    }
    for case in cases:
        event = build_full_ocsf_event(case)
        assert required <= set(event)
        assert event["type_uid"] == event["class_uid"] * 100 + event["activity_id"]
        assert event["metadata"]["version"] == OCSF_VERSION
        assert event["metadata"]["product"]["name"] == "Worldshepherd SARA"
        assert event["severity_id"] == 1
        if event["class_uid"] != 0:
            assert "actor" in event


def test_worldshepherd_native_fields_are_kept_out_of_top_level_ocsf_namespace():
    for case in _cases():
        fixture = build_interop_fixture(case)
        event = build_full_ocsf_event(case)
        assert "worldshepherd" not in event
        native = event["unmapped"]["worldshepherd"]
        assert native["source_fixture_digest"] == fixture.correlation.ws_evidence_digest
        grains = {
            event["metadata"]["uid"],
            native["ws_session_uid"],
            native["ws_turn_uid"],
            native["ws_invocation_uid"],
            native["ws_policy_decision_uid"],
        }
        assert len(grains) == 5


def test_remote_tool_cases_use_api_activity_with_required_material():
    for case in _cases():
        if case.action_kind != "remote_tool":
            continue
        event = build_full_ocsf_event(case)
        assert event["class_uid"] == 6003
        assert event["category_uid"] == 6
        assert event["api"]["operation"]
        assert event["api"]["request"]["uid"]
        assert event["src_endpoint"]["ip"] == "192.0.2.10"
        assert "actor" in event


def test_local_process_cases_use_base_event_when_source_has_no_device_identity():
    for case in _cases():
        if case.action_kind != "local_process":
            continue
        event = build_full_ocsf_event(case)
        native = event["unmapped"]["worldshepherd"]
        assert event["class_uid"] == 0
        assert event["category_uid"] == 0
        assert event["activity_id"] == 99
        assert event["type_uid"] == 99
        assert "device" not in event
        assert "actor" not in event
        assert "process" not in event
        assert native["source_process"]["uid"] == native["ws_invocation_uid"]
        assert native["source_process"]["name"] == "fixture-command"
        assert "no device identity" in event["message"].lower()


def test_non_hostless_file_cases_keep_file_activity_shape_if_added_later():
    for case in _cases():
        if case.action_kind != "file_operation" or case.hostless:
            continue
        event = build_full_ocsf_event(case)
        assert event["class_uid"] == 1001
        assert event["category_uid"] == 1
        assert event["file"]["name"] == "fixture.txt"
        assert event["file"]["type_id"] == 1


def test_hostless_source_uses_generic_base_event_instead_of_fabricating_device():
    case = next(case for case in _cases() if case.case_id == "INT-FILE-READ-HOSTLESS")
    event = build_full_ocsf_event(case)
    native = event["unmapped"]["worldshepherd"]

    assert case.hostless is True
    assert event["class_uid"] == 0
    assert event["class_name"] == "Base Event"
    assert event["category_uid"] == 0
    assert event["category_name"] == "Uncategorized"
    assert event["activity_id"] == 99
    assert event["activity_name"] == "Other"
    assert event["type_uid"] == 99
    assert "device" not in event
    assert "actor" not in event
    assert "file" not in event
    assert native["hostless"] is True
    assert native["source_file"]["name"] == "fixture.txt"
    assert native["source_file"]["path"] == "/synthetic/fixture.txt"
    assert "no device identity" in event["message"].lower()


def test_denied_interrupted_and_readonly_mismatch_states_remain_explicit():
    indexed = {case.case_id: case for case in _cases()}

    denied = build_full_ocsf_event(indexed["INT-REMOTE-DENY"])
    assert denied["status_id"] == 2
    assert denied["status"] == "Failure"
    assert denied["unmapped"]["worldshepherd"]["action_executed"] is False

    interrupted = build_full_ocsf_event(indexed["INT-INTERRUPTED"])
    assert interrupted["status_id"] == 99
    assert interrupted["status"] == "Interrupted"
    assert interrupted["unmapped"]["worldshepherd"]["action_executed"] is False

    mismatch = build_full_ocsf_event(indexed["INT-READONLY-MISMATCH"])
    assert mismatch["unmapped"]["worldshepherd"]["declared_readonly"] is True
    assert mismatch["unmapped"]["worldshepherd"]["observed_operation"] == "WRITE"
    assert indexed["INT-READONLY-MISMATCH"].expected_outcome == ExpectedOutcome.SUCCESS
