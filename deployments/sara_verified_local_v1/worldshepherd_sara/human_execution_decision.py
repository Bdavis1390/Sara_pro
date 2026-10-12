from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


HUMAN_EXECUTION_DECISION_SCHEMA = "WS-HUMAN-EXECUTION-DECISION-V1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class HumanExecutionAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    DEFER = "DEFER"


class HumanExecutionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal[HUMAN_EXECUTION_DECISION_SCHEMA] = HUMAN_EXECUTION_DECISION_SCHEMA
    decision_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    action_digest_sha256: str = Field(pattern=_SHA256_PATTERN)
    decision_by: str = Field(min_length=1, max_length=512)
    decided_at: datetime
    action: HumanExecutionAction
    rationale: str = Field(min_length=1, max_length=4096)
    decision_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_contract(self) -> "HumanExecutionDecision":
        if self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware")
        return self


class HumanExecutionDecisionError(ValueError):
    pass


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def record_human_execution_decision(
    *,
    decision_id: str,
    action_id: str,
    action_digest_sha256: str,
    decision_by: str,
    decided_at: datetime,
    action: HumanExecutionAction,
    rationale: str,
) -> HumanExecutionDecision:
    if decided_at.tzinfo is None:
        raise HumanExecutionDecisionError("decided_at must be timezone-aware")
    provisional = HumanExecutionDecision(
        decision_id=decision_id,
        action_id=action_id,
        action_digest_sha256=action_digest_sha256,
        decision_by=decision_by,
        decided_at=decided_at,
        action=action,
        rationale=rationale,
        decision_sha256="sha256:" + "0" * 64,
    )
    body = provisional.model_dump(mode="json", exclude={"decision_sha256"})
    return provisional.model_copy(update={"decision_sha256": _sha256_json(body)})


def verify_human_execution_decision(record: HumanExecutionDecision) -> bool:
    body = record.model_dump(mode="json", exclude={"decision_sha256"})
    return _sha256_json(body) == record.decision_sha256


def assert_human_approval_matches(
    record: HumanExecutionDecision,
    *,
    action_id: str,
    action_digest_sha256: str,
) -> None:
    if not verify_human_execution_decision(record):
        raise HumanExecutionDecisionError("human decision record integrity check failed")
    if record.action is not HumanExecutionAction.APPROVE:
        raise HumanExecutionDecisionError("human decision is not APPROVE")
    if record.action_id != action_id:
        raise HumanExecutionDecisionError("human approval action identity mismatch")
    if record.action_digest_sha256 != action_digest_sha256:
        raise HumanExecutionDecisionError("human approval action digest mismatch")
