"""WS-SOE v0.1A contract gate.

This module provides a deliberately small, fail-closed contract layer for
binding intent, authorization, observation, evidence, and conformance without
collapsing missing or contradictory evidence into success.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Mapping, Sequence

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "ws-soe/v0.1a"
DEMO_ACTION = "demo.counter.increment"
DEMO_TARGET = "demo.counter"


class WSSOEError(RuntimeError):
    """Base error for the WS-SOE contract gate."""


class AuthorizationError(WSSOEError):
    """Authorization is absent, denied, future-dated, or not exactly bound."""


class ExpiredIntentError(AuthorizationError):
    """The intent is not currently inside its validity window."""


class ReplayError(AuthorizationError):
    """An already-consumed intent was presented for execution again."""


class UnsupportedActionError(WSSOEError):
    """The demo executor was asked to perform an unsupported action."""


class TargetSubstitutionError(WSSOEError):
    """The demo executor was asked to act on a target other than the bound target."""


class DecisionOutcome(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class ConformanceStatus(str, Enum):
    MATCH = "MATCH"
    DEVIATION = "DEVIATION"
    VIOLATION = "VIOLATION"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    CONFLICT = "CONFLICT"


def _normalize(value: Any) -> Any:
    """Convert supported values to deterministic JSON-compatible primitives."""
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical timestamps must be timezone-aware")
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            normalized[key] = _normalize(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not canonicalizable")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Return deterministic UTF-8 JSON text for contract hashing."""
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    """Return a prefixed SHA-256 digest over deterministic canonical JSON."""
    payload = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class _Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: str = Field(default=SCHEMA_VERSION, pattern=r"^ws-soe/v0\.1a$")


class Intent(_Contract):
    intent_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    nonce: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract(self) -> "Intent":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        canonical_json(self.arguments)
        return self


class Decision(_Contract):
    decision_id: str = Field(min_length=1)
    intent_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    outcome: DecisionOutcome
    decided_at: AwareDatetime
    authority: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class Observation(_Contract):
    observation_id: str = Field(min_length=1)
    intent_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    observed_at: AwareDatetime
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payloads(self) -> "Observation":
        canonical_json(self.before)
        canonical_json(self.after)
        canonical_json(self.result)
        return self


class EvidenceReceipt(_Contract):
    receipt_id: str = Field(min_length=1)
    intent_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    observation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    previous_receipt_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    emitted_at: AwareDatetime


class ConformanceAssessment(_Contract):
    assessment_id: str = Field(min_length=1)
    intent_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: ConformanceStatus
    reason: str = Field(min_length=1)
    assessed_at: AwareDatetime
    decision_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    observation_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


def authorize_intent(
    intent: Intent,
    *,
    decision_id: str,
    authority: str,
    decided_at: datetime,
    outcome: DecisionOutcome = DecisionOutcome.ALLOW,
    reason: str = "bounded demo authorization",
) -> Decision:
    """Create a decision that is cryptographically bound to the exact intent bytes."""
    return Decision(
        decision_id=decision_id,
        intent_hash=canonical_sha256(intent),
        outcome=outcome,
        decided_at=decided_at,
        authority=authority,
        reason=reason,
    )


def validate_authorization(intent: Intent, decision: Decision, *, now: datetime) -> None:
    """Fail closed unless an ALLOW decision exactly binds a currently valid intent."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    if now_utc < intent.issued_at.astimezone(UTC):
        raise ExpiredIntentError("intent is not active yet")
    if now_utc >= intent.expires_at.astimezone(UTC):
        raise ExpiredIntentError("intent has expired")
    if decision.outcome != DecisionOutcome.ALLOW:
        raise AuthorizationError("decision does not allow execution")
    if decision.decided_at.astimezone(UTC) < intent.issued_at.astimezone(UTC):
        raise AuthorizationError("decision predates the intent validity window")
    if decision.decided_at.astimezone(UTC) > now_utc:
        raise AuthorizationError("decision is future-dated")
    expected = canonical_sha256(intent)
    if decision.intent_hash != expected:
        raise AuthorizationError("decision is not bound to the exact current intent")


def make_evidence_receipt(
    intent: Intent,
    observation: Observation,
    *,
    receipt_id: str,
    emitted_at: datetime,
    previous_receipt: EvidenceReceipt | None = None,
) -> EvidenceReceipt:
    """Bind an observation to an intent and, optionally, to the previous receipt."""
    return EvidenceReceipt(
        receipt_id=receipt_id,
        intent_hash=canonical_sha256(intent),
        observation_hash=canonical_sha256(observation),
        previous_receipt_hash=(
            canonical_sha256(previous_receipt) if previous_receipt is not None else None
        ),
        emitted_at=emitted_at,
    )


def verify_evidence_chain(receipts: Sequence[EvidenceReceipt]) -> bool:
    """Verify exact predecessor digests for an ordered receipt chain."""
    if not receipts:
        return False
    previous: EvidenceReceipt | None = None
    for receipt in receipts:
        expected_previous = canonical_sha256(previous) if previous is not None else None
        if receipt.previous_receipt_hash != expected_previous:
            return False
        previous = receipt
    return True


class DemoCounterExecutor:
    """In-memory, bounded executor used only for the harmless v0.1A trace."""

    def __init__(self, initial_value: int = 41) -> None:
        if isinstance(initial_value, bool) or not isinstance(initial_value, int):
            raise TypeError("initial_value must be an integer")
        self._value = initial_value
        self._consumed_intent_hashes: set[str] = set()

    @property
    def value(self) -> int:
        return self._value

    def execute(
        self,
        intent: Intent,
        decision: Decision,
        *,
        now: datetime,
        observation_id: str,
    ) -> Observation:
        validate_authorization(intent, decision, now=now)
        intent_hash = canonical_sha256(intent)
        if intent_hash in self._consumed_intent_hashes:
            raise ReplayError("intent has already been consumed")
        if intent.action != DEMO_ACTION:
            raise UnsupportedActionError(f"unsupported demo action: {intent.action}")
        if intent.target != DEMO_TARGET:
            raise TargetSubstitutionError(f"unsupported demo target: {intent.target}")
        if intent.arguments != {"delta": 1}:
            raise UnsupportedActionError("demo.counter.increment requires exactly {'delta': 1}")

        before = self._value
        self._value += 1
        self._consumed_intent_hashes.add(intent_hash)
        return Observation(
            observation_id=observation_id,
            intent_hash=intent_hash,
            action=intent.action,
            target=intent.target,
            observed_at=now,
            before={"counter": before},
            after={"counter": self._value},
            result={"applied_delta": 1},
        )


def _assessment(
    intent: Intent,
    *,
    status: ConformanceStatus,
    reason: str,
    assessed_at: datetime,
    decision: Decision | None,
    observation: Observation | None,
    evidence: EvidenceReceipt | None,
) -> ConformanceAssessment:
    intent_hash = canonical_sha256(intent)
    decision_hash = canonical_sha256(decision) if decision is not None else None
    observation_hash = canonical_sha256(observation) if observation is not None else None
    evidence_hash = canonical_sha256(evidence) if evidence is not None else None
    seed = {
        "intent_hash": intent_hash,
        "status": status,
        "reason": reason,
        "assessed_at": assessed_at,
        "decision_hash": decision_hash,
        "observation_hash": observation_hash,
        "evidence_hash": evidence_hash,
    }
    assessment_id = "ws-soe-assessment-" + canonical_sha256(seed).split(":", 1)[1][:24]
    return ConformanceAssessment(
        assessment_id=assessment_id,
        intent_hash=intent_hash,
        status=status,
        reason=reason,
        assessed_at=assessed_at,
        decision_hash=decision_hash,
        observation_hash=observation_hash,
        evidence_hash=evidence_hash,
    )


def assess_conformance(
    intent: Intent,
    *,
    decision: Decision | None,
    observation: Observation | None,
    receipts: Sequence[EvidenceReceipt] = (),
    assessed_at: datetime,
    max_observation_age: timedelta = timedelta(seconds=30),
) -> ConformanceAssessment:
    """Derive one of six non-collapsible conformance states from supplied evidence."""
    if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
        raise ValueError("assessed_at must be timezone-aware")
    if max_observation_age <= timedelta(0):
        raise ValueError("max_observation_age must be positive")

    latest_receipt = receipts[-1] if receipts else None
    expected_intent_hash = canonical_sha256(intent)

    if decision is None:
        return _assessment(
            intent,
            status=ConformanceStatus.UNKNOWN,
            reason="authorization evidence unavailable",
            assessed_at=assessed_at,
            decision=None,
            observation=observation,
            evidence=latest_receipt,
        )
    if decision.intent_hash != expected_intent_hash:
        return _assessment(
            intent,
            status=ConformanceStatus.CONFLICT,
            reason="decision intent binding conflicts with the supplied intent",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if observation is None:
        return _assessment(
            intent,
            status=ConformanceStatus.UNKNOWN,
            reason="execution observation unavailable",
            assessed_at=assessed_at,
            decision=decision,
            observation=None,
            evidence=latest_receipt,
        )
    if observation.intent_hash != expected_intent_hash:
        return _assessment(
            intent,
            status=ConformanceStatus.CONFLICT,
            reason="observation intent binding conflicts with the supplied intent",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )

    age = assessed_at.astimezone(UTC) - observation.observed_at.astimezone(UTC)
    if age < timedelta(0):
        return _assessment(
            intent,
            status=ConformanceStatus.CONFLICT,
            reason="observation is future-dated relative to assessment",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if age > max_observation_age:
        return _assessment(
            intent,
            status=ConformanceStatus.STALE,
            reason="observation exceeded the maximum accepted age",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )

    if not receipts:
        return _assessment(
            intent,
            status=ConformanceStatus.UNKNOWN,
            reason="evidence receipt unavailable",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=None,
        )
    if not verify_evidence_chain(receipts):
        return _assessment(
            intent,
            status=ConformanceStatus.CONFLICT,
            reason="evidence receipt chain failed predecessor-hash verification",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if any(receipt.intent_hash != expected_intent_hash for receipt in receipts):
        return _assessment(
            intent,
            status=ConformanceStatus.CONFLICT,
            reason="evidence receipt intent binding conflicts with the supplied intent",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    expected_observation_hash = canonical_sha256(observation)
    if latest_receipt is None or latest_receipt.observation_hash != expected_observation_hash:
        return _assessment(
            intent,
            status=ConformanceStatus.CONFLICT,
            reason="latest evidence receipt does not bind the supplied observation",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )

    if decision.outcome == DecisionOutcome.DENY:
        return _assessment(
            intent,
            status=ConformanceStatus.VIOLATION,
            reason="execution was observed despite an explicit deny decision",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if decision.decided_at.astimezone(UTC) < intent.issued_at.astimezone(UTC):
        return _assessment(
            intent,
            status=ConformanceStatus.VIOLATION,
            reason="allow decision predates the intent validity window",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if not (
        intent.issued_at.astimezone(UTC)
        <= observation.observed_at.astimezone(UTC)
        < intent.expires_at.astimezone(UTC)
    ):
        return _assessment(
            intent,
            status=ConformanceStatus.VIOLATION,
            reason="execution observation falls outside the intent validity window",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if observation.action != intent.action or observation.target != intent.target:
        return _assessment(
            intent,
            status=ConformanceStatus.VIOLATION,
            reason="observed action or target falls outside the authorized intent",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )

    if intent.action != DEMO_ACTION or intent.target != DEMO_TARGET:
        return _assessment(
            intent,
            status=ConformanceStatus.UNKNOWN,
            reason="no v0.1A conformance rule exists for this action and target",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if intent.arguments != {"delta": 1}:
        return _assessment(
            intent,
            status=ConformanceStatus.UNKNOWN,
            reason="demo action arguments are outside the v0.1A rule",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )

    before = observation.before.get("counter")
    after = observation.after.get("counter")
    applied_delta = observation.result.get("applied_delta")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (before, after, applied_delta)):
        return _assessment(
            intent,
            status=ConformanceStatus.UNKNOWN,
            reason="observation lacks integer counter evidence required by the demo rule",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )
    if after != before + 1 or applied_delta != 1:
        return _assessment(
            intent,
            status=ConformanceStatus.DEVIATION,
            reason="observed counter transition differs from the authorized increment",
            assessed_at=assessed_at,
            decision=decision,
            observation=observation,
            evidence=latest_receipt,
        )

    return _assessment(
        intent,
        status=ConformanceStatus.MATCH,
        reason="authorization, execution observation, evidence binding, and outcome agree",
        assessed_at=assessed_at,
        decision=decision,
        observation=observation,
        evidence=latest_receipt,
    )
