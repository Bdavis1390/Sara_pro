from __future__ import annotations

from typing import Any

from .standards_interop import (
    ExpectedOutcome,
    InteropCaseDefinition,
    InteropFixture,
    ObservedOperation,
    build_interop_fixture,
)

GEMARA_SCHEMA_COMMIT = "24e52e93bc71e28507e1942ce543e26ab58a7f25"
GEMARA_VERSION = "v0.17.0-dev"
FIXTURE_TIMESTAMP = "2026-09-12T00:00:00Z"


def _actor() -> dict[str, Any]:
    return {
        "id": "worldshepherd-sara",
        "name": "Worldshepherd SARA",
        "type": "Software",
        "version": "0.1.0",
        "description": "Synthetic interoperability fixture generator",
    }


def _target() -> dict[str, Any]:
    return {
        "id": "worldshepherd-sara-control-plane",
        "name": "Worldshepherd SARA control plane",
        "type": "Software",
        "version": "0.1.0",
        "environment": "synthetic-interoperability-test",
    }


def _mapping_references(case: InteropCaseDefinition) -> list[dict[str, Any]]:
    return [
        {
            "id": "ws-control",
            "title": "Worldshepherd interoperability controls",
            "version": "0.1",
            "description": "Synthetic control and assessment requirements used by the interoperability fixture corpus.",
        },
        {
            "id": "ws-policy",
            "title": "Worldshepherd governed-action policy",
            "version": "0.1",
            "description": "Synthetic policy-method reference used to exercise authorization and enforcement evidence.",
        },
        {
            "id": "ws-ocsf-event",
            "title": "Worldshepherd OCSF-oriented source event",
            "version": "0.1",
            "description": f"Originating operational evidence for {case.case_id}.",
        },
        {
            "id": "ws-evaluation",
            "title": "Worldshepherd Gemara evaluation projection",
            "version": "0.2",
            "description": f"Evaluation log projection for {case.case_id}.",
        },
        {
            "id": "ws-criteria",
            "title": "Worldshepherd interoperability audit criteria",
            "version": "0.2",
            "description": "Synthetic audit criterion for authorization/action/evidence consistency.",
        },
    ]


def _metadata(case: InteropCaseDefinition, artifact_type: str, suffix: str) -> dict[str, Any]:
    return {
        "id": f"{case.case_id}:{suffix}",
        "type": artifact_type,
        "gemara-version": GEMARA_VERSION,
        "version": "0.2",
        "date": FIXTURE_TIMESTAMP,
        "description": (
            "Worldshepherd synthetic interoperability evidence projection. "
            "This document is test material and does not assert external certification."
        ),
        "author": _actor(),
        "mapping-references": _mapping_references(case),
        "draft": True,
    }


def _evidence(fixture: InteropFixture) -> dict[str, Any]:
    return {
        "id": f"{fixture.case.case_id}:ocsf-evidence",
        "type": "OCSF Event",
        "collected-at": FIXTURE_TIMESTAMP,
        "source": {
            "reference-id": "ws-ocsf-event",
            "coordinate": f"case/{fixture.case.case_id}/ocsf_event",
            "digest": fixture.correlation.ws_evidence_digest,
            "remarks": "Digest pins the canonicalized originating event used by this synthetic fixture.",
        },
        "description": "Originating operational event evidence.",
    }


def _assessment_result(fixture: InteropFixture) -> str:
    if "DECLARED_READONLY_BEHAVIOR_MISMATCH" in fixture.expected_flags:
        return "Needs Review"
    if fixture.case.expected_outcome == ExpectedOutcome.DENIED:
        return "Failed"
    if fixture.case.expected_outcome == ExpectedOutcome.INTERRUPTED:
        return "Unknown"
    return "Passed"


def build_full_gemara_documents(case: InteropCaseDefinition) -> dict[str, dict[str, Any]]:
    fixture = build_interop_fixture(case)
    result = _assessment_result(fixture)

    control_ref = {"reference-id": "ws-control", "entry-id": "WS-INTEROP-CTRL-001"}
    requirement_ref = {"reference-id": "ws-control", "entry-id": "WS-INTEROP-REQ-001"}
    policy_method_ref = {"reference-id": "ws-policy", "entry-id": "WS-METHOD-GOVERNED-ACTION"}
    policy_plan_ref = {"reference-id": "ws-policy", "entry-id": "WS-PLAN-GOVERNED-ACTION"}

    evaluation = {
        "metadata": _metadata(case, "EvaluationLog", "evaluation"),
        "target": _target(),
        "result": result,
        "evaluations": [
            {
                "name": "Authorization, action, and evidence consistency",
                "result": result,
                "message": (
                    "Synthetic control evaluation over the frozen Worldshepherd interoperability fixture."
                ),
                "control": control_ref,
                "assessment-logs": [
                    {
                        "requirement": requirement_ref,
                        "plan": policy_plan_ref,
                        "description": "Evaluate authorization/action/evidence consistency for one fixture case.",
                        "result": result,
                        "message": f"Case {case.case_id} evaluated as {result}.",
                        "applicability": ["synthetic interoperability fixture"],
                        "steps": [
                            "Build deterministic operational fixture",
                            "Verify authorization and execution invariant",
                            "Verify evidence digest binding",
                        ],
                        "steps-executed": 3,
                        "start": FIXTURE_TIMESTAMP,
                        "end": FIXTURE_TIMESTAMP,
                        "confidence-level": "High",
                        "evidence": [_evidence(fixture)],
                    }
                ],
            }
        ],
    }

    if result == "Passed":
        disposition = "Clear"
    elif result == "Failed":
        disposition = "Enforced"
    else:
        disposition = "Undetermined"

    enforcement = {
        "metadata": _metadata(case, "EnforcementLog", "enforcement"),
        "target": _target(),
        "disposition": disposition,
        "actions": [
            {
                "disposition": disposition,
                "method": policy_method_ref,
                "message": (
                    "Synthetic enforcement projection derived from the same frozen interoperability fixture."
                ),
                "start": FIXTURE_TIMESTAMP,
                "end": FIXTURE_TIMESTAMP,
                "steps": [
                    "Read recorded policy decision",
                    "Correlate action execution state",
                    "Record enforcement disposition",
                ],
                "justification": {
                    "assessments": [
                        {
                            "result": result,
                            "requirement": requirement_ref,
                            "plan": policy_plan_ref,
                            "log": {
                                "reference-id": "ws-evaluation",
                                "entry-id": f"{case.case_id}:evaluation",
                            },
                        }
                    ]
                },
            }
        ],
    }

    result_type = {
        "Passed": "Strength",
        "Failed": "Finding",
        "Needs Review": "Observation",
        "Unknown": "Observation",
    }[result]

    audit_result: dict[str, Any] = {
        "id": f"{case.case_id}:audit-result",
        "title": "Authorization/action/evidence consistency",
        "type": result_type,
        "description": f"Frozen synthetic case produced Gemara evaluation result {result}.",
        "criteria-reference": {
            "reference-id": "ws-criteria",
            "entries": [
                {
                    "reference-id": "ws-criteria",
                    "remarks": "WS-GOV-CRITERION-001",
                }
            ],
        },
        "evidence": [_evidence(fixture)],
    }
    if result != "Passed":
        audit_result["recommendations"] = [
            {
                "id": f"{case.case_id}:recommendation",
                "text": "Retain the non-passing state and require explicit review before any trust-state upgrade.",
                "required": True,
            }
        ]

    audit = {
        "metadata": _metadata(case, "AuditLog", "audit"),
        "target": _target(),
        "summary": (
            "Synthetic audit projection over the frozen Worldshepherd interoperability evidence chain."
        ),
        "criteria": [
            {
                "reference-id": "ws-criteria",
                "remarks": "WS-GOV-CRITERION-001: authorization, execution state, and evidence binding remain consistent.",
            }
        ],
        "results": [audit_result],
    }

    return {
        "evaluation": evaluation,
        "enforcement": enforcement,
        "audit": audit,
    }
