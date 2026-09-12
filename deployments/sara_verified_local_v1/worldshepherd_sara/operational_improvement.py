from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, model_validator

from .echo_event_store import EchoStoredEvent, semantic_sha256
from .improvement_cycle import ImprovementProposal, ImprovementRisk, ImprovementState, ImprovementTriggerKind
from .models import AuditRecord
from .qualification import CapabilityStatus, canonical_digest

_SIGNAL_KEY = "_ws_improvement_signal"
_ALLOWED = {
    ImprovementTriggerKind.NEW_EVIDENCE,
    ImprovementTriggerKind.TEST_RESULT,
    ImprovementTriggerKind.FAILURE,
    ImprovementTriggerKind.ANOMALY,
    ImprovementTriggerKind.CONTRADICTION,
    ImprovementTriggerKind.SECURITY_EVENT,
    ImprovementTriggerKind.OPERATOR_FEEDBACK,
}

class OperationalImprovementSignalError(ValueError):
    pass

class OperationalImprovementSignal(BaseModel):
    source: str = Field(min_length=1)
    trigger_kind: ImprovementTriggerKind
    statement: str = Field(min_length=1)
    affected_lanes: list[str] = Field(min_length=1)
    risk_level: ImprovementRisk = ImprovementRisk.MODERATE
    baseline_capability_status: list[CapabilityStatus] = Field(default_factory=list)
    baseline_artifacts: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    reversible: bool = True

    @model_validator(mode="after")
    def validate_signal(self):
        if self.source not in {"ECHO", "OVERWATCH"}:
            raise ValueError("unsupported operational source")
        if self.trigger_kind not in _ALLOWED:
            raise ValueError("unsupported operational trigger")
        return self

def _stable_id(record: AuditRecord) -> str:
    event_id = record.payload.get("_outbox_event_id")
    if not isinstance(event_id, str):
        raise OperationalImprovementSignalError("valid ECHO event id required")
    year = record.timestamp[:4]
    digest = canonical_digest({"event_id": event_id}).split(":", 1)[1]
    return f"WS-IR-{year}-{int(digest[:12], 16)}"

def _signal(record: AuditRecord) -> OperationalImprovementSignal:
    raw = record.payload.get(_SIGNAL_KEY)
    if not isinstance(raw, dict):
        raise OperationalImprovementSignalError("explicit WS-RI signal required")
    try:
        return OperationalImprovementSignal.model_validate(raw)
    except ValueError as exc:
        raise OperationalImprovementSignalError("invalid WS-RI signal") from exc

def audit_event_to_improvement(record: AuditRecord, *, created_utc: str) -> ImprovementProposal:
    digest = semantic_sha256(record)
    signal = _signal(record)
    event_id = str(record.payload["_outbox_event_id"])
    baseline = list(dict.fromkeys(signal.baseline_capability_status)) or [CapabilityStatus.NOT_CURRENTLY_CLAIMED]
    tests = list(dict.fromkeys([
        f"{event_id}:echo-semantic-integrity",
        f"{event_id}:observation-gate",
        *signal.required_tests,
    ]))
    metrics = list(dict.fromkeys(signal.success_metrics)) or ["all required validation tests pass"]
    risks = ["observation does not promote capability maturity"]
    if signal.source == "OVERWATCH":
        risks.append("producer label does not establish runtime validation")
    return ImprovementProposal(
        improvement_id=_stable_id(record),
        trigger_kind=signal.trigger_kind,
        title=f"{signal.source} improvement candidate: {record.event}",
        source_refs=[event_id, f"ECHO-SEMANTIC-SHA256:{digest}"],
        affected_lanes=list(dict.fromkeys([signal.source, *signal.affected_lanes, "WS-RI"])),
        baseline_artifacts=list(dict.fromkeys(signal.baseline_artifacts)),
        baseline_capability_status=baseline,
        target_capability_status=None,
        proposed_change="Evaluate this operational signal through existing qualification and authorization gates: " + signal.statement,
        expected_benefit="Create a traceable improvement candidate from explicit operational evidence.",
        assumptions=["ECHO semantic validation remains authoritative."],
        risks=risks,
        risk_level=signal.risk_level,
        required_tests=tests,
        success_metrics=metrics,
        negative_evidence=list(signal.negative_evidence),
        reversible=signal.reversible,
        generated_by=f"{signal.source}->ECHO->WS-RI",
        created_utc=created_utc,
        state=ImprovementState.PROPOSED,
        requested_claim_promotion=False,
        requested_external_execution=False,
    )

def stored_echo_event_to_improvement(stored: EchoStoredEvent, *, created_utc: str) -> ImprovementProposal:
    record = AuditRecord(timestamp=stored.first_audit_timestamp, event=stored.event, actor=stored.actor, payload=stored.payload())
    if semantic_sha256(record) != stored.semantic_sha256:
        raise OperationalImprovementSignalError("stored ECHO event failed semantic verification")
    return audit_event_to_improvement(record, created_utc=created_utc)
