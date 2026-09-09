from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .autonomy_policy import (
    AutonomyPolicy,
    AutonomousActionCandidate,
    ExecutionDisposition,
    evaluate_candidate,
)
from .interoperability import InterfaceContract
from .qualification import canonical_digest


class ExternalInterfaceActivation(BaseModel):
    """Evidence gate for any future partner-owned interface activation.

    The synthetic harness is intentionally usable without partner documentation,
    but no external interface may be represented as enabled unless authoritative
    specification identity and partner-validation evidence are supplied.
    """

    enabled: bool = False
    authoritative_spec_ref: str | None = None
    authoritative_spec_digest: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    partner_validation_ref: str | None = None

    @model_validator(mode="after")
    def enabled_requires_authoritative_evidence(self) -> "ExternalInterfaceActivation":
        if self.enabled and not (
            self.authoritative_spec_ref
            and self.authoritative_spec_digest
            and self.partner_validation_ref
        ):
            raise ValueError(
                "external interface activation requires authoritative specification "
                "identity, digest, and partner-validation reference"
            )
        return self

    def claims_boundary(self) -> str:
        if self.enabled:
            return (
                "Partner-validated interface activation metadata is present only for "
                "the stated specification and evidence scope; no certification, "
                "government acceptance, or operational effectiveness is inferred."
            )
        return (
            "Synthetic/internal interface work only; no partner API access, platform "
            "interoperability, certification, or operational deployment is claimed."
        )


class NeutralMissionEvent(BaseModel):
    """Worldshepherd-owned neutral event envelope for synthetic mission testing."""

    schema_version: Literal["ws-neutral-mission-event/1"] = "ws-neutral-mission-event/1"
    event_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    observed_utc: datetime
    sequence: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def timestamp_must_be_timezone_aware(self) -> "NeutralMissionEvent":
        if self.observed_utc.tzinfo is None or self.observed_utc.utcoffset() is None:
            raise ValueError("observed_utc must be timezone-aware")
        return self

    def digest(self) -> str:
        return canonical_digest(self)

    def idempotency_key(self) -> str:
        return canonical_digest(
            {
                "schema_version": self.schema_version,
                "source_system": self.source_system,
                "mission_id": self.mission_id,
                "event_id": self.event_id,
            }
        )


class SyntheticEvidenceRecord(BaseModel):
    evidence_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mission_id: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    observed_utc: datetime
    evidence_scope: Literal["SIMULATION"] = "SIMULATION"
    capability_status: Literal["SIMULATED_ONLY"] = "SIMULATED_ONLY"
    external_command_emitted: Literal[False] = False


class AdapterObservation(BaseModel):
    event: NeutralMissionEvent
    evidence: SyntheticEvidenceRecord
    accepted: bool
    duplicate: bool
    external_command_emitted: Literal[False] = False


class SupervisoryEvaluation(BaseModel):
    action_id: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    disposition: ExecutionDisposition
    reasons: list[str] = Field(default_factory=list)
    external_command_emitted: Literal[False] = False


class SyntheticMissionAdapter:
    """Read-only vendor-neutral adapter harness for WS-XOS-MA-001 preparation.

    This class deliberately has no HTTP client, socket transport, platform command
    method, or XTEND/XOS field mapping. It accepts only the Worldshepherd-owned
    neutral event envelope and produces internal evidence plus policy evaluations.
    Partner-specific transport/mapping must be implemented separately after the
    applicable NDA/export-control and authoritative-interface gates are satisfied.
    """

    def __init__(
        self,
        *,
        contract: InterfaceContract,
        activation: ExternalInterfaceActivation | None = None,
    ) -> None:
        self.contract = contract
        self.activation = activation or ExternalInterfaceActivation()
        if self.activation.enabled:
            raise ValueError(
                "synthetic adapter cannot activate a partner-owned external interface"
            )
        self._seen: set[str] = set()

    def _validate_contract(self, event: NeutralMissionEvent) -> None:
        if (
            self.contract.required_message_types
            and event.event_type not in self.contract.required_message_types
        ):
            raise ValueError(
                f"event type {event.event_type!r} is not allowed by synthetic contract"
            )
        required_fields = self.contract.required_fields.get(event.event_type, [])
        missing = [field for field in required_fields if field not in event.payload]
        if missing:
            raise ValueError(
                f"event payload missing contracted fields: {sorted(missing)}"
            )

    def _evidence(self, event: NeutralMissionEvent) -> SyntheticEvidenceRecord:
        event_digest = event.digest()
        contract_digest = self.contract.digest()
        evidence_id = canonical_digest(
            {
                "event_digest": event_digest,
                "contract_digest": contract_digest,
                "evidence_scope": "SIMULATION",
                "capability_status": "SIMULATED_ONLY",
            }
        )
        return SyntheticEvidenceRecord(
            evidence_id=evidence_id,
            event_digest=event_digest,
            contract_digest=contract_digest,
            mission_id=event.mission_id,
            source_system=event.source_system,
            event_type=event.event_type,
            observed_utc=event.observed_utc,
        )

    def ingest(self, payload: dict[str, Any]) -> AdapterObservation:
        event = NeutralMissionEvent.model_validate(payload)
        self._validate_contract(event)
        evidence = self._evidence(event)
        key = event.idempotency_key()
        if key in self._seen:
            return AdapterObservation(
                event=event,
                evidence=evidence,
                accepted=False,
                duplicate=True,
            )
        self._seen.add(key)
        return AdapterObservation(
            event=event,
            evidence=evidence,
            accepted=True,
            duplicate=False,
        )

    def evaluate_supervisory_request(
        self,
        *,
        candidate: AutonomousActionCandidate,
        policy: AutonomyPolicy,
    ) -> SupervisoryEvaluation:
        disposition, reasons = evaluate_candidate(candidate, policy)
        return SupervisoryEvaluation(
            action_id=candidate.action_id,
            policy_id=policy.policy_id,
            disposition=disposition,
            reasons=reasons,
        )

    def claims_boundary(self) -> str:
        return self.activation.claims_boundary()
