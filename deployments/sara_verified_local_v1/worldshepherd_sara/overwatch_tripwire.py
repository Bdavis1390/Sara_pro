from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .storage import DurableStore


OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY = "ws_overwatch_containment_intents_v1"
OVERWATCH_DECISION_SCHEMA = "WS-OVERWATCH-TRIPWIRE-DECISION-V1"
OVERWATCH_CONTAINMENT_INTENT_SCHEMA = "WS-OVERWATCH-CONTAINMENT-INTENT-V1"
MAX_OVERWATCH_CONTAINMENT_INTENTS = 1024


class OverwatchTripwireError(RuntimeError):
    """Raised when OVERWATCH state cannot be evaluated or recorded safely."""


class OverwatchDisposition(str, Enum):
    CONTINUE = "CONTINUE"
    CONSTRAIN = "CONSTRAIN"
    CONTAIN = "CONTAIN"
    TERMINATE = "TERMINATE"


class OverwatchSignal(str, Enum):
    MONITORING_SUPPRESSION = "MONITORING_SUPPRESSION"
    GOVERNING_POLICY_ALTERATION = "GOVERNING_POLICY_ALTERATION"
    SANDBOX_ESCAPE = "SANDBOX_ESCAPE"
    UNAUTHORIZED_REPLICATION = "UNAUTHORIZED_REPLICATION"
    CONTAINMENT_BYPASS_ATTEMPT = "CONTAINMENT_BYPASS_ATTEMPT"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    UNAUTHORIZED_CREDENTIAL_USE = "UNAUTHORIZED_CREDENTIAL_USE"
    UNAUTHORIZED_PERSISTENCE = "UNAUTHORIZED_PERSISTENCE"
    UNEXPECTED_NETWORK_EGRESS = "UNEXPECTED_NETWORK_EGRESS"
    UNAUTHORIZED_CHILD_AGENT_CREATION = "UNAUTHORIZED_CHILD_AGENT_CREATION"
    RESOURCE_CEILING_BREACH = "RESOURCE_CEILING_BREACH"
    TOOL_USE_DIVERGENCE = "TOOL_USE_DIVERGENCE"


class _Severity(IntEnum):
    CONTINUE = 0
    CONSTRAIN = 1
    CONTAIN = 2
    TERMINATE = 3


_TERMINATE_SIGNALS = frozenset(
    {
        OverwatchSignal.MONITORING_SUPPRESSION,
        OverwatchSignal.GOVERNING_POLICY_ALTERATION,
        OverwatchSignal.SANDBOX_ESCAPE,
        OverwatchSignal.UNAUTHORIZED_REPLICATION,
        OverwatchSignal.CONTAINMENT_BYPASS_ATTEMPT,
    }
)
_CONTAIN_SIGNALS = frozenset(
    {
        OverwatchSignal.PRIVILEGE_ESCALATION,
        OverwatchSignal.UNAUTHORIZED_CREDENTIAL_USE,
        OverwatchSignal.UNAUTHORIZED_PERSISTENCE,
        OverwatchSignal.UNEXPECTED_NETWORK_EGRESS,
        OverwatchSignal.UNAUTHORIZED_CHILD_AGENT_CREATION,
    }
)
_CONSTRAIN_SIGNALS = frozenset(
    {
        OverwatchSignal.RESOURCE_CEILING_BREACH,
        OverwatchSignal.TOOL_USE_DIVERGENCE,
    }
)


_SIGNAL_REASONS: dict[OverwatchSignal, str] = {
    OverwatchSignal.MONITORING_SUPPRESSION: "independent monitoring suppression was detected",
    OverwatchSignal.GOVERNING_POLICY_ALTERATION: "governing safety-policy alteration was detected",
    OverwatchSignal.SANDBOX_ESCAPE: "sandbox escape was detected",
    OverwatchSignal.UNAUTHORIZED_REPLICATION: "unauthorized replication was detected",
    OverwatchSignal.CONTAINMENT_BYPASS_ATTEMPT: "containment bypass attempt was detected",
    OverwatchSignal.PRIVILEGE_ESCALATION: "unauthorized privilege escalation was detected",
    OverwatchSignal.UNAUTHORIZED_CREDENTIAL_USE: "unauthorized credential use was detected",
    OverwatchSignal.UNAUTHORIZED_PERSISTENCE: "unauthorized persistence was detected",
    OverwatchSignal.UNEXPECTED_NETWORK_EGRESS: "unexpected network egress was detected",
    OverwatchSignal.UNAUTHORIZED_CHILD_AGENT_CREATION: "unauthorized child-agent creation was detected",
    OverwatchSignal.RESOURCE_CEILING_BREACH: "resource ceiling was breached",
    OverwatchSignal.TOOL_USE_DIVERGENCE: "tool-use behavior diverged from the governed execution envelope",
}


class OverwatchObservation(BaseModel):
    """A monitor observation presented to the deterministic tripwire classifier.

    This schema does not authenticate the monitor. Monitor identity and telemetry
    authenticity remain a later runtime-integration gate and must not be inferred
    from the presence of ``monitor_id`` alone.
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=160)
    monitor_id: str = Field(min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=160)
    model_version: str = Field(min_length=1, max_length=160)
    observed_at: datetime
    telemetry_complete: bool = True
    monitor_heartbeat_present: bool = True
    signals: tuple[OverwatchSignal, ...] = Field(default_factory=tuple, max_length=32)

    @model_validator(mode="after")
    def validate_observation(self) -> "OverwatchObservation":
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if len(set(self.signals)) != len(self.signals):
            raise ValueError("signals must not contain duplicates")
        return self


class OverwatchDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal["WS-OVERWATCH-TRIPWIRE-DECISION-V1"] = OVERWATCH_DECISION_SCHEMA
    observation_id: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=160)
    monitor_id: str = Field(min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=160)
    model_version: str = Field(min_length=1, max_length=160)
    observed_at: datetime
    disposition: OverwatchDisposition
    triggered_signals: tuple[OverwatchSignal, ...] = Field(max_length=32)
    reasons: tuple[str, ...] = Field(min_length=1, max_length=40)
    decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_effect: Literal["NONE"] = "NONE"

    @model_validator(mode="after")
    def validate_decision(self) -> "OverwatchDecision":
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if len(set(self.triggered_signals)) != len(self.triggered_signals):
            raise ValueError("triggered_signals must not contain duplicates")
        return self


class OverwatchContainmentIntent(BaseModel):
    """Durable non-authorizing intent record.

    ``execution_effect_applied`` is intentionally pinned to False in Phase 8A.
    A later actuator layer must use a distinct schema and verification gate before
    any containment side effect can be claimed.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal["WS-OVERWATCH-CONTAINMENT-INTENT-V1"] = (
        OVERWATCH_CONTAINMENT_INTENT_SCHEMA
    )
    observation_id: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=160)
    monitor_id: str = Field(min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=160)
    model_version: str = Field(min_length=1, max_length=160)
    observed_at: datetime
    recorded_at: datetime
    disposition: Literal[
        OverwatchDisposition.CONSTRAIN,
        OverwatchDisposition.CONTAIN,
        OverwatchDisposition.TERMINATE,
    ]
    triggered_signals: tuple[OverwatchSignal, ...] = Field(max_length=32)
    reasons: tuple[str, ...] = Field(min_length=1, max_length=40)
    decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False

    @model_validator(mode="after")
    def validate_times(self) -> "OverwatchContainmentIntent":
        for field_name, value in (
            ("observed_at", self.observed_at),
            ("recorded_at", self.recorded_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        return self


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _signal_severity(signal: OverwatchSignal) -> _Severity:
    if signal in _TERMINATE_SIGNALS:
        return _Severity.TERMINATE
    if signal in _CONTAIN_SIGNALS:
        return _Severity.CONTAIN
    if signal in _CONSTRAIN_SIGNALS:
        return _Severity.CONSTRAIN
    raise OverwatchTripwireError(f"unclassified OVERWATCH signal: {signal.value}")


def classify_overwatch_observation(observation: OverwatchObservation) -> OverwatchDecision:
    """Return a deterministic fail-closed disposition for one monitor observation."""

    severity = _Severity.CONTINUE
    reasons: set[str] = set()
    ordered_signals = tuple(sorted(observation.signals, key=lambda signal: signal.value))

    for signal in ordered_signals:
        severity = max(severity, _signal_severity(signal))
        reasons.add(_SIGNAL_REASONS[signal])

    # Missing monitor heartbeat or incomplete telemetry cannot prove a malicious
    # action, so Phase 8A classifies them as CONTAIN rather than TERMINATE. This
    # remains fail closed without overstating the evidence.
    if not observation.monitor_heartbeat_present:
        severity = max(severity, _Severity.CONTAIN)
        reasons.add("independent monitor heartbeat is absent")
    if not observation.telemetry_complete:
        severity = max(severity, _Severity.CONTAIN)
        reasons.add("required monitoring telemetry is incomplete")

    disposition = {
        _Severity.CONTINUE: OverwatchDisposition.CONTINUE,
        _Severity.CONSTRAIN: OverwatchDisposition.CONSTRAIN,
        _Severity.CONTAIN: OverwatchDisposition.CONTAIN,
        _Severity.TERMINATE: OverwatchDisposition.TERMINATE,
    }[severity]

    if not reasons:
        reasons.add("no configured tripwire or monitoring-integrity failure was detected")

    ordered_reasons = tuple(sorted(reasons))
    digest = _digest_payload(
        {
            "schema": OVERWATCH_DECISION_SCHEMA,
            "observation_id": observation.observation_id,
            "action_id": observation.action_id,
            "monitor_id": observation.monitor_id,
            "model_id": observation.model_id,
            "model_version": observation.model_version,
            "observed_at": _utc_iso(observation.observed_at),
            "disposition": disposition.value,
            "triggered_signals": [signal.value for signal in ordered_signals],
            "reasons": list(ordered_reasons),
            "authorization_effect": "NONE",
        }
    )

    return OverwatchDecision(
        observation_id=observation.observation_id,
        action_id=observation.action_id,
        monitor_id=observation.monitor_id,
        model_id=observation.model_id,
        model_version=observation.model_version,
        observed_at=observation.observed_at,
        disposition=disposition,
        triggered_signals=ordered_signals,
        reasons=ordered_reasons,
        decision_digest_sha256=digest,
    )


def _intent_matches_decision(
    intent: OverwatchContainmentIntent,
    decision: OverwatchDecision,
) -> bool:
    return (
        intent.observation_id == decision.observation_id
        and intent.action_id == decision.action_id
        and intent.monitor_id == decision.monitor_id
        and intent.model_id == decision.model_id
        and intent.model_version == decision.model_version
        and intent.observed_at == decision.observed_at
        and intent.disposition.value == decision.disposition.value
        and intent.triggered_signals == decision.triggered_signals
        and intent.reasons == decision.reasons
        and intent.decision_digest_sha256 == decision.decision_digest_sha256
        and intent.authorization_effect == "NONE"
        and intent.execution_effect_applied is False
    )


def record_overwatch_containment_intent(
    store: DurableStore,
    *,
    decision: OverwatchDecision,
    now: datetime | None = None,
) -> OverwatchContainmentIntent:
    """Persist CONSTRAIN/CONTAIN/TERMINATE intent without applying side effects.

    Duplicate replay of the exact same decision is idempotent. Reuse of an
    observation ID for different semantics fails closed. The registry is capped;
    Phase 8A never silently evicts containment evidence.
    """

    if decision.disposition == OverwatchDisposition.CONTINUE:
        raise OverwatchTripwireError(
            "CONTINUE decisions do not create containment intent records"
        )

    recorded_at = now or datetime.now(timezone.utc)
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise OverwatchTripwireError("recorded_at must be timezone-aware")

    new_intent = OverwatchContainmentIntent(
        observation_id=decision.observation_id,
        action_id=decision.action_id,
        monitor_id=decision.monitor_id,
        model_id=decision.model_id,
        model_version=decision.model_version,
        observed_at=decision.observed_at,
        recorded_at=recorded_at,
        disposition=decision.disposition,
        triggered_signals=decision.triggered_signals,
        reasons=decision.reasons,
        decision_digest_sha256=decision.decision_digest_sha256,
    )

    def transaction(
        registry: dict[str, object],
    ) -> tuple[dict[str, object] | None, OverwatchContainmentIntent]:
        raw_namespace = registry.get(OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY, {})
        if not isinstance(raw_namespace, dict):
            raise OverwatchTripwireError(
                "OVERWATCH containment-intent registry namespace is malformed"
            )

        validated: dict[str, OverwatchContainmentIntent] = {}
        for observation_id, raw_record in raw_namespace.items():
            if not isinstance(observation_id, str) or not isinstance(raw_record, dict):
                raise OverwatchTripwireError(
                    "OVERWATCH containment-intent registry contains malformed records"
                )
            try:
                record = OverwatchContainmentIntent.model_validate(raw_record)
            except Exception as exc:  # pydantic ValidationError without broad dependency here
                raise OverwatchTripwireError(
                    "OVERWATCH containment-intent registry contains invalid records"
                ) from exc
            if record.observation_id != observation_id:
                raise OverwatchTripwireError(
                    "OVERWATCH containment-intent registry key/record identity mismatch"
                )
            validated[observation_id] = record

        existing = validated.get(decision.observation_id)
        if existing is not None:
            if not _intent_matches_decision(existing, decision):
                raise OverwatchTripwireError(
                    "observation ID replay conflicts with existing containment intent"
                )
            return None, existing

        if len(validated) >= MAX_OVERWATCH_CONTAINMENT_INTENTS:
            raise OverwatchTripwireError(
                "OVERWATCH containment-intent registry capacity reached; no evidence was evicted"
            )

        updated_namespace = dict(raw_namespace)
        updated_namespace[decision.observation_id] = new_intent.model_dump(mode="json")
        return {OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY: updated_namespace}, new_intent

    return store.transact_registry(transaction)
