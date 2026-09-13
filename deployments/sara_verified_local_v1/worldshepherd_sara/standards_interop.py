from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .qualification import canonical_digest


CORPUS_SCHEMA = "WS-STANDARDS-INTEROP-CORPUS-V0.1"
OCSF_TARGET = "OCSF-1.10.0-dev-PROPOSAL-COMPATIBLE"
GEMARA_TARGET = "GEMARA-1.1-COMPATIBLE"
EXTERNAL_VALIDATION_STATUS = "NOT_RUN"


class AuthorizationMode(str, Enum):
    POLICY_APPROVED = "POLICY_APPROVED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    DENIED = "DENIED"


class ObservedOperation(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"


class ExpectedOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    INTERRUPTED = "INTERRUPTED"


class InteropCaseDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    action_kind: str = Field(min_length=1)
    authorization_mode: AuthorizationMode
    hostless: bool = False
    declared_readonly: bool | None = None
    observed_operation: ObservedOperation
    expected_outcome: ExpectedOutcome
    interrupted: bool = False

    @model_validator(mode="after")
    def outcome_consistency(self) -> "InteropCaseDefinition":
        if self.authorization_mode == AuthorizationMode.DENIED and self.expected_outcome != ExpectedOutcome.DENIED:
            raise ValueError("DENIED authorization requires DENIED outcome")
        if self.expected_outcome == ExpectedOutcome.INTERRUPTED and not self.interrupted:
            raise ValueError("INTERRUPTED outcome requires interrupted=true")
        return self


class CorrelationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ws_event_uid: str = Field(min_length=1)
    ws_session_uid: str = Field(min_length=1)
    ws_turn_uid: str = Field(min_length=1)
    ws_invocation_uid: str = Field(min_length=1)
    ws_policy_decision_uid: str = Field(min_length=1)
    ws_evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def identifiers_preserve_grain(self) -> "CorrelationContract":
        ids = {
            self.ws_event_uid,
            self.ws_session_uid,
            self.ws_turn_uid,
            self.ws_invocation_uid,
            self.ws_policy_decision_uid,
        }
        if len(ids) != 5:
            raise ValueError("event, session, turn, invocation, and policy-decision identifiers must be distinct")
        return self


class InteropFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: str = CORPUS_SCHEMA
    case: InteropCaseDefinition
    correlation: CorrelationContract
    ocsf_target: str = OCSF_TARGET
    gemara_target: str = GEMARA_TARGET
    external_validation_status: str = EXTERNAL_VALIDATION_STATUS
    ocsf_event: dict[str, Any]
    gemara_evaluation_log: dict[str, Any]
    gemara_enforcement_log: dict[str, Any]
    gemara_audit_log: dict[str, Any]
    expected_flags: list[str] = Field(default_factory=list)
    claims_boundary: str = (
        "Internal interoperability fixture only; no OCSF or Gemara certification, "
        "partner validation, government acceptance, or operational interoperability is claimed."
    )

    @model_validator(mode="after")
    def validate_evidence_chain(self) -> "InteropFixture":
        observed = canonical_digest(self.ocsf_event)
        if observed != self.correlation.ws_evidence_digest:
            raise ValueError("OCSF event digest does not match ws_evidence_digest")

        if self.case.hostless and "device" in self.ocsf_event:
            raise ValueError("hostless fixtures must not fabricate device identity")

        action_executed = bool(self.ocsf_event.get("worldshepherd", {}).get("action_executed"))
        if self.case.expected_outcome == ExpectedOutcome.DENIED and action_executed:
            raise ValueError("denied fixture cannot record action execution")
        if self.case.expected_outcome == ExpectedOutcome.INTERRUPTED:
            status = self.ocsf_event.get("status")
            if status == "Success":
                raise ValueError("interrupted fixture cannot report silent success")

        for document in (
            self.gemara_evaluation_log,
            self.gemara_enforcement_log,
            self.gemara_audit_log,
        ):
            evidence_digest = document.get("worldshepherd-evidence-digest")
            if evidence_digest != self.correlation.ws_evidence_digest:
                raise ValueError("Gemara-compatible document does not bind to originating event digest")
        return self


def _uid(case_id: str, grain: str) -> str:
    return f"{case_id}:{grain}"


def _authorization(case: InteropCaseDefinition, policy_uid: str) -> dict[str, Any]:
    if case.authorization_mode == AuthorizationMode.HUMAN_APPROVED:
        decision = "Approved"
        authority = "human"
    elif case.authorization_mode == AuthorizationMode.POLICY_APPROVED:
        decision = "Allowed"
        authority = "policy"
    else:
        decision = "Denied"
        authority = "policy"
    return {
        "decision": decision,
        "policy": {"uid": policy_uid},
        "worldshepherd_authority_kind": authority,
    }


def _ocsf_class(case: InteropCaseDefinition) -> tuple[int, str, int, str]:
    if case.action_kind == "remote_tool":
        return 6003, "API Activity", 99, "Invoke"
    if case.action_kind == "local_process":
        return 1007, "Process Activity", 1, "Launch"
    if case.action_kind == "file_operation":
        activity_id = 2 if case.observed_operation == ObservedOperation.READ else 3
        activity_name = "Read" if case.observed_operation == ObservedOperation.READ else "Update"
        return 1001, "File System Activity", activity_id, activity_name
    return 6003, "API Activity", 99, "Other"


def build_interop_fixture(case: InteropCaseDefinition) -> InteropFixture:
    event_uid = _uid(case.case_id, "event")
    session_uid = _uid(case.case_id, "session")
    turn_uid = _uid(case.case_id, "turn")
    invocation_uid = _uid(case.case_id, "invocation")
    policy_uid = _uid(case.case_id, "policy-decision")

    class_uid, class_name, activity_id, activity_name = _ocsf_class(case)
    action_executed = case.expected_outcome == ExpectedOutcome.SUCCESS
    status = {
        ExpectedOutcome.SUCCESS: "Success",
        ExpectedOutcome.DENIED: "Failure",
        ExpectedOutcome.INTERRUPTED: "Interrupted",
    }[case.expected_outcome]

    event: dict[str, Any] = {
        "class_uid": class_uid,
        "class_name": class_name,
        "activity_id": activity_id,
        "activity_name": activity_name,
        "status": status,
        "metadata": {
            "uid": event_uid,
            "correlation_uid": turn_uid,
            "worldshepherd_schema_target": OCSF_TARGET,
            "worldshepherd_external_validation_status": EXTERNAL_VALIDATION_STATUS,
        },
        "actor": {
            "app_name": "Worldshepherd SARA",
            "authorizations": [_authorization(case, policy_uid)],
        },
        "ai_agent": {
            "uid": "worldshepherd-sara",
            "instance_uid": session_uid,
            "name": "SARA",
        },
        "worldshepherd": {
            "turn_uid": turn_uid,
            "invocation_uid": invocation_uid,
            "policy_decision_uid": policy_uid,
            "action_executed": action_executed,
        },
    }

    if not case.hostless:
        event["device"] = {"uid": f"fixture-host:{case.case_id}", "name": "synthetic-fixture-host"}

    if case.action_kind == "remote_tool":
        event["api"] = {
            "operation": "fixture/tool_call",
            "request": {"uid": invocation_uid},
            "service": {"name": "fixture-service"},
        }
        # OCSF ai_tool is still proposal-stage in upstream PR #1729. Keep it explicitly
        # namespaced as draft material instead of claiming current released-schema validity.
        event["worldshepherd"]["draft_ai_tool"] = {
            "name": "fixture_tool",
            "uid": "fixture-service/fixture_tool",
            "transaction_uid": invocation_uid,
            "is_readonly": case.declared_readonly,
        }
    elif case.action_kind == "local_process":
        event["process"] = {"uid": invocation_uid, "name": "fixture-command", "cmd_line": "fixture-command --dry-run"}
    elif case.action_kind == "file_operation":
        event["file"] = {"name": "fixture.txt", "path": "/synthetic/fixture.txt"}

    digest = canonical_digest(event)

    flags: list[str] = []
    if case.declared_readonly is True and case.observed_operation in {ObservedOperation.WRITE, ObservedOperation.EXECUTE}:
        flags.append("DECLARED_READONLY_BEHAVIOR_MISMATCH")
    if case.hostless:
        flags.append("HOSTLESS_SOURCE_NO_FABRICATED_DEVICE")
    if case.expected_outcome == ExpectedOutcome.DENIED:
        flags.append("DENIED_NO_ACTION_EXECUTION")
    if case.expected_outcome == ExpectedOutcome.INTERRUPTED:
        flags.append("INTERRUPTED_EXPLICIT_NON_SUCCESS")

    evidence_source = {
        "reference-id": "worldshepherd-ocsf-fixture",
        "coordinate": f"case/{case.case_id}/ocsf_event",
        "digest": digest,
    }

    evaluation = {
        "metadata": {"id": f"{case.case_id}:evaluation", "type": "EvaluationLog"},
        "result": "Passed" if not flags or flags == ["HOSTLESS_SOURCE_NO_FABRICATED_DEVICE"] else "Needs Review",
        "worldshepherd-evidence-digest": digest,
        "worldshepherd-evidence-source": evidence_source,
        "worldshepherd-schema-target": GEMARA_TARGET,
        "worldshepherd-external-validation-status": EXTERNAL_VALIDATION_STATUS,
    }

    enforcement = {
        "metadata": {"id": f"{case.case_id}:enforcement", "type": "EnforcementLog"},
        "disposition": {
            AuthorizationMode.POLICY_APPROVED: "Clear",
            AuthorizationMode.HUMAN_APPROVED: "Clear",
            AuthorizationMode.DENIED: "Enforced",
        }[case.authorization_mode],
        "worldshepherd-policy-decision-uid": policy_uid,
        "worldshepherd-evidence-digest": digest,
        "worldshepherd-evidence-source": evidence_source,
        "worldshepherd-schema-target": GEMARA_TARGET,
        "worldshepherd-external-validation-status": EXTERNAL_VALIDATION_STATUS,
    }

    audit = {
        "metadata": {"id": f"{case.case_id}:audit", "type": "AuditLog"},
        "summary": "Worldshepherd OCSF/Gemara interoperability fixture audit",
        "worldshepherd-flags": flags,
        "worldshepherd-evidence-digest": digest,
        "worldshepherd-evidence-source": evidence_source,
        "worldshepherd-schema-target": GEMARA_TARGET,
        "worldshepherd-external-validation-status": EXTERNAL_VALIDATION_STATUS,
    }

    correlation = CorrelationContract(
        ws_event_uid=event_uid,
        ws_session_uid=session_uid,
        ws_turn_uid=turn_uid,
        ws_invocation_uid=invocation_uid,
        ws_policy_decision_uid=policy_uid,
        ws_evidence_digest=digest,
    )

    return InteropFixture(
        case=case,
        correlation=correlation,
        ocsf_event=event,
        gemara_evaluation_log=evaluation,
        gemara_enforcement_log=enforcement,
        gemara_audit_log=audit,
        expected_flags=flags,
    )


def verify_fixture_integrity(fixture: InteropFixture) -> bool:
    return canonical_digest(fixture.ocsf_event) == fixture.correlation.ws_evidence_digest
