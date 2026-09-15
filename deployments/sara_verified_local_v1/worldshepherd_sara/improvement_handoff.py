from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .autonomy_policy import ExecutionDisposition
from .improvement_feedback import ImprovementFeedbackPolicy
from .improvement_runtime import ImprovementRuntime, ImprovementRuntimeError
from .qualification import canonical_digest


HANDOFF_SCHEMA = "ws-ri-scheduler-handoff-1"


class ImprovementHandoffAction(StrEnum):
    RUN_ONE_BOUNDED_FEEDBACK_CYCLE = "RUN_ONE_BOUNDED_FEEDBACK_CYCLE"


class ImprovementSchedulerHandoff(BaseModel):
    schema: str = HANDOFF_SCHEMA
    handoff_id: str = Field(pattern=r"^WS-RI-HANDOFF-[A-F0-9]{16}$")
    action: ImprovementHandoffAction
    requested_by: str = Field(min_length=1)
    generated_utc: str = Field(min_length=1)
    ledger_head_digest: str | None = None
    feedback_cursor_digest: str = Field(min_length=1)
    max_echo_events: int = Field(ge=1, le=4096)
    max_new_proposals: int = Field(ge=1, le=1024)
    execution_disposition: ExecutionDisposition = ExecutionDisposition.HUMAN_REVIEW_REQUIRED
    authorization_required: bool = True
    autonomous_execution_authorized: bool = False
    claim_promotion_authorized: bool = False
    deployment_authorized: bool = False
    external_execution_authorized: bool = False
    claims_boundary: str = Field(min_length=1)
    handoff_digest: str = Field(min_length=1)

    @model_validator(mode="after")
    def fail_closed(self) -> "ImprovementSchedulerHandoff":
        if self.execution_disposition != ExecutionDisposition.HUMAN_REVIEW_REQUIRED:
            raise ValueError("WS-RI handoff must remain human/authorized-scheduler gated")
        if not self.authorization_required:
            raise ValueError("WS-RI handoff must require authorization")
        if any(
            (
                self.autonomous_execution_authorized,
                self.claim_promotion_authorized,
                self.deployment_authorized,
                self.external_execution_authorized,
            )
        ):
            raise ValueError("WS-RI handoff cannot grant execution, promotion, or deployment authority")
        return self


def _handoff_payload(
    runtime: ImprovementRuntime,
    *,
    requested_by: str,
    generated_utc: str,
    policy: ImprovementFeedbackPolicy,
) -> dict[str, object]:
    if not requested_by.strip() or not generated_utc.strip():
        raise ImprovementRuntimeError("requested_by and generated_utc are required")
    status = runtime.status()
    if not status["ledger_chain_verified"]:
        raise ImprovementRuntimeError("WS-RI ledger chain must verify before scheduler handoff")
    if not status["echo_source_configured"]:
        raise ImprovementRuntimeError("WS-RI ECHO source is required for feedback handoff")
    return {
        "schema": HANDOFF_SCHEMA,
        "action": ImprovementHandoffAction.RUN_ONE_BOUNDED_FEEDBACK_CYCLE.value,
        "requested_by": requested_by.strip(),
        "generated_utc": generated_utc.strip(),
        "ledger_head_digest": status["head_record_digest"],
        "feedback_cursor_digest": status["feedback_cursor_digest"],
        "max_echo_events": policy.max_echo_events_per_cycle,
        "max_new_proposals": policy.max_new_proposals_per_cycle,
        "execution_disposition": ExecutionDisposition.HUMAN_REVIEW_REQUIRED.value,
        "authorization_required": True,
        "autonomous_execution_authorized": False,
        "claim_promotion_authorized": False,
        "deployment_authorized": False,
        "external_execution_authorized": False,
        "claims_boundary": (
            "handoff artifact only; an identified operator or separately authorized scheduler "
            "must invoke one bounded feedback cycle; no claim promotion or deployment authority"
        ),
    }


def build_scheduler_handoff(
    runtime: ImprovementRuntime,
    *,
    requested_by: str,
    generated_utc: str,
    policy: ImprovementFeedbackPolicy | None = None,
) -> ImprovementSchedulerHandoff:
    active = policy or ImprovementFeedbackPolicy()
    payload = _handoff_payload(
        runtime,
        requested_by=requested_by,
        generated_utc=generated_utc,
        policy=active,
    )
    digest = canonical_digest(payload)
    raw = digest.split(":", 1)[-1].upper()
    return ImprovementSchedulerHandoff(
        **payload,
        handoff_id=f"WS-RI-HANDOFF-{raw[:16]}",
        handoff_digest=digest,
    )


def verify_scheduler_handoff(handoff: ImprovementSchedulerHandoff) -> bool:
    material = handoff.model_dump(mode="json")
    observed_digest = str(material.pop("handoff_digest"))
    handoff_id = str(material.pop("handoff_id"))
    expected_digest = canonical_digest(material)
    expected_id = f"WS-RI-HANDOFF-{expected_digest.split(':', 1)[-1].upper()[:16]}"
    return observed_digest == expected_digest and handoff_id == expected_id
