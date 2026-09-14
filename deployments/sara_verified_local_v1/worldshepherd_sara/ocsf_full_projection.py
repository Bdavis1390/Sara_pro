from __future__ import annotations

from typing import Any

from .standards_interop import (
    AuthorizationMode,
    ExpectedOutcome,
    InteropCaseDefinition,
    ObservedOperation,
    build_interop_fixture,
)


OCSF_SCHEMA_COMMIT = "c1ab05a382ffc97250997ffe010f3f715a097c2a"
OCSF_COMPILER_COMMIT = "865887a9ee88580c471062f93da115e7599fa31d"
OCSF_TOOLKIT_COMMIT = "a99619fcd148791a6a9fe5f82c1e0d839f658591"
OCSF_VERSION = "1.10.0-dev"
FIXTURE_TIME_MS = 1789161600000


def _classification(case: InteropCaseDefinition) -> tuple[int, str, int, str, int, str]:
    if case.action_kind == "remote_tool":
        activity_id = {
            ObservedOperation.READ: 2,
            ObservedOperation.WRITE: 3,
            ObservedOperation.EXECUTE: 99,
        }[case.observed_operation]
        activity_name = {
            2: "Read",
            3: "Update",
            99: "Other",
        }[activity_id]
        return 6003, "API Activity", 6, "Application Activity", activity_id, activity_name

    if case.action_kind == "local_process":
        return 1007, "Process Activity", 1, "System Activity", 1, "Launch"

    if case.action_kind == "file_operation" and case.hostless:
        # File System Activity requires a device in the pinned OCSF schema. A
        # hostless producer has no truthful device identity to provide, so use
        # the concrete generic Base Event rather than manufacturing one.
        return 0, "Base Event", 0, "Uncategorized", 99, "Other"

    if case.action_kind == "file_operation":
        activity_id = 2 if case.observed_operation == ObservedOperation.READ else 3
        activity_name = "Read" if activity_id == 2 else "Update"
        return 1001, "File System Activity", 1, "System Activity", activity_id, activity_name

    raise ValueError(f"unsupported action_kind: {case.action_kind}")


def _status(case: InteropCaseDefinition) -> tuple[int, str]:
    if case.expected_outcome == ExpectedOutcome.SUCCESS:
        return 1, "Success"
    if case.expected_outcome == ExpectedOutcome.DENIED:
        return 2, "Failure"
    if case.expected_outcome == ExpectedOutcome.INTERRUPTED:
        return 99, "Interrupted"
    raise ValueError(f"unsupported expected_outcome: {case.expected_outcome}")


def _actor(case: InteropCaseDefinition, policy_uid: str) -> dict[str, Any]:
    decision = "Denied" if case.authorization_mode == AuthorizationMode.DENIED else "Allowed"
    return {
        "application": {
            "uid": "worldshepherd-sara",
            "name": "Worldshepherd SARA",
            "version": "0.1.0",
        },
        "authorizations": [
            {
                "decision": decision,
                "policy": {
                    "uid": policy_uid,
                    "name": "Worldshepherd governed-action policy",
                    "type": "Governed action authorization",
                    "is_applied": True,
                },
            }
        ],
    }


def build_full_ocsf_event(case: InteropCaseDefinition) -> dict[str, Any]:
    """Build a strict OCSF-oriented projection without mutating the frozen source fixture.

    Worldshepherd-native correlation and governance fields that are not settled OCSF
    attributes remain under ``unmapped``. The frozen source fixture and its digest are
    preserved separately as evidence; this derived event receives its own canonical
    representation and can be validated independently.
    """

    fixture = build_interop_fixture(case)
    correlation = fixture.correlation

    class_uid, class_name, category_uid, category_name, activity_id, activity_name = _classification(case)
    status_id, status = _status(case)
    type_uid = class_uid * 100 + activity_id

    native: dict[str, Any] = {
        "ws_session_uid": correlation.ws_session_uid,
        "ws_turn_uid": correlation.ws_turn_uid,
        "ws_invocation_uid": correlation.ws_invocation_uid,
        "ws_policy_decision_uid": correlation.ws_policy_decision_uid,
        "source_fixture_digest": correlation.ws_evidence_digest,
        "authorization_mode": case.authorization_mode.value,
        "action_executed": case.expected_outcome == ExpectedOutcome.SUCCESS,
        "declared_readonly": case.declared_readonly,
        "observed_operation": case.observed_operation.value,
        "hostless": case.hostless,
    }

    event: dict[str, Any] = {
        "activity_id": activity_id,
        "activity_name": activity_name,
        "category_uid": category_uid,
        "category_name": category_name,
        "class_uid": class_uid,
        "class_name": class_name,
        "type_uid": type_uid,
        "type_name": f"{class_name}: {activity_name}",
        "severity_id": 1,
        "severity": "Informational",
        "time": FIXTURE_TIME_MS,
        "status_id": status_id,
        "status": status,
        "metadata": {
            "uid": correlation.ws_event_uid,
            "correlation_uid": correlation.ws_turn_uid,
            "version": OCSF_VERSION,
            "product": {
                "uid": "worldshepherd-sara",
                "name": "Worldshepherd SARA",
                "vendor_name": "Worldshepherd",
                "version": "0.1.0",
            },
        },
        "unmapped": {"worldshepherd": native},
    }

    # Base Event does not define actor. Keep hostless producer/governance
    # semantics in the vendor-neutral escape hatch rather than adding an
    # unsupported top-level attribute.
    if class_uid != 0:
        event["actor"] = _actor(case, correlation.ws_policy_decision_uid)

    if case.action_kind == "remote_tool":
        event["api"] = {
            "operation": f"fixture.tool.{case.observed_operation.value.lower()}",
            "request": {"uid": correlation.ws_invocation_uid},
            "service": {"name": "fixture-service"},
        }
        event["src_endpoint"] = {
            "ip": "192.0.2.10",
            "uid": f"fixture-client:{case.case_id}",
        }

    elif case.action_kind == "local_process":
        event["process"] = {
            "uid": correlation.ws_invocation_uid,
            "name": "fixture-command",
            "cmd_line": "fixture-command --dry-run",
        }

    elif case.action_kind == "file_operation" and case.hostless:
        native["source_file"] = {
            "name": "fixture.txt",
            "path": "/synthetic/fixture.txt",
            "type_id": 1,
            "type": "Regular File",
        }
        event["message"] = "Hostless file read observed; no device identity supplied by source."

    elif case.action_kind == "file_operation":
        event["file"] = {
            "name": "fixture.txt",
            "path": "/synthetic/fixture.txt",
            "type_id": 1,
            "type": "Regular File",
        }

    return event
