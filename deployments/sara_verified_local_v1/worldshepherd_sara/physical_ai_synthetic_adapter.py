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
from .models import AuditRecord
from .qualification import canonical_digest
from .storage import DurableStore


_PERSISTENCE_REGISTRY_KEY = "ws_xos_ma_001_synthetic_adapter_v1"


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

    When a ``DurableStore`` is supplied, accepted-event identity and evidence are
    persisted under the contract digest so identical events remain deduplicated
    after adapter reconstruction/restart. This is local single-store persistence,
    not a distributed exactly-once protocol or partner-platform acknowledgement.
    """

    def __init__(
        self,
        *,
        contract: InterfaceContract,
        activation: ExternalInterfaceActivation | None = None,
        store: DurableStore | None = None,
    ) -> None:
        self.contract = contract
        self.activation = activation or ExternalInterfaceActivation()
        if self.activation.enabled:
            raise ValueError(
                "synthetic adapter cannot activate a partner-owned external interface"
            )
        self.store = store
        self._contract_digest = self.contract.digest()
        self._seen: dict[str, tuple[str, SyntheticEvidenceRecord]] = self._load_seen()

    def _validate_contract(self, event: NeutralMissionEvent) -> None:
        if event.event_type not in self.contract.required_message_types:
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
        evidence_id = canonical_digest(
            {
                "event_digest": event_digest,
                "contract_digest": self._contract_digest,
                "evidence_scope": "SIMULATION",
                "capability_status": "SIMULATED_ONLY",
            }
        )
        return SyntheticEvidenceRecord(
            evidence_id=evidence_id,
            event_digest=event_digest,
            contract_digest=self._contract_digest,
            mission_id=event.mission_id,
            source_system=event.source_system,
            event_type=event.event_type,
            observed_utc=event.observed_utc,
        )

    def _load_seen(self) -> dict[str, tuple[str, SyntheticEvidenceRecord]]:
        if self.store is None:
            return {}
        registry = self.store.get_registry()
        root = registry.get(_PERSISTENCE_REGISTRY_KEY, {})
        if not isinstance(root, dict):
            raise ValueError("synthetic adapter persistence root must be an object")
        contracts = root.get("contracts", {})
        if not isinstance(contracts, dict):
            raise ValueError("synthetic adapter persistence contracts must be an object")
        contract_state = contracts.get(self._contract_digest, {})
        if not isinstance(contract_state, dict):
            raise ValueError("synthetic adapter contract persistence must be an object")
        events = contract_state.get("events", {})
        if not isinstance(events, dict):
            raise ValueError("synthetic adapter persisted events must be an object")

        seen: dict[str, tuple[str, SyntheticEvidenceRecord]] = {}
        for key, value in events.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError("synthetic adapter persisted event entry is invalid")
            digest = value.get("event_digest")
            evidence_payload = value.get("evidence")
            if not isinstance(digest, str) or not isinstance(evidence_payload, dict):
                raise ValueError("synthetic adapter persisted event evidence is invalid")
            evidence = SyntheticEvidenceRecord.model_validate(evidence_payload)
            if evidence.event_digest != digest:
                raise ValueError("synthetic adapter persisted event digest mismatch")
            if evidence.contract_digest != self._contract_digest:
                raise ValueError("synthetic adapter persisted contract digest mismatch")
            seen[key] = (digest, evidence)
        return seen

    def _persist_seen(
        self, key: str, evidence: SyntheticEvidenceRecord
    ) -> None:
        if self.store is None:
            return
        registry = self.store.get_registry()
        root = registry.get(_PERSISTENCE_REGISTRY_KEY, {})
        if not isinstance(root, dict):
            raise ValueError("synthetic adapter persistence root must be an object")
        contracts = root.get("contracts", {})
        if not isinstance(contracts, dict):
            raise ValueError("synthetic adapter persistence contracts must be an object")
        contract_state = contracts.get(self._contract_digest, {})
        if not isinstance(contract_state, dict):
            raise ValueError("synthetic adapter contract persistence must be an object")
        events = contract_state.get("events", {})
        if not isinstance(events, dict):
            raise ValueError("synthetic adapter persisted events must be an object")

        events = dict(events)
        events[key] = {
            "event_digest": evidence.event_digest,
            "evidence": evidence.model_dump(mode="json"),
        }
        contract_state = dict(contract_state)
        contract_state["events"] = events
        contracts = dict(contracts)
        contracts[self._contract_digest] = contract_state
        root = dict(root)
        root["contracts"] = contracts
        self.store.patch_registry({_PERSISTENCE_REGISTRY_KEY: root})
        self.store.append_audit(
            AuditRecord.create(
                event="synthetic_mission_event_persisted",
                actor="system",
                payload={
                    "contract_digest": self._contract_digest,
                    "idempotency_key": key,
                    "event_digest": evidence.event_digest,
                    "evidence_id": evidence.evidence_id,
                },
            )
        )

    def _audit_collision(
        self, key: str, *, prior_digest: str, current_digest: str
    ) -> None:
        if self.store is None:
            return
        self.store.append_audit(
            AuditRecord.create(
                event="synthetic_mission_event_idempotency_collision",
                actor="system",
                payload={
                    "contract_digest": self._contract_digest,
                    "idempotency_key": key,
                    "prior_event_digest": prior_digest,
                    "current_event_digest": current_digest,
                },
            )
        )

    def ingest(self, payload: dict[str, Any]) -> AdapterObservation:
        event = NeutralMissionEvent.model_validate(payload)
        self._validate_contract(event)
        evidence = self._evidence(event)
        key = event.idempotency_key()

        prior = self._seen.get(key)
        if prior is not None:
            prior_digest, prior_evidence = prior
            if prior_digest != evidence.event_digest:
                self._audit_collision(
                    key,
                    prior_digest=prior_digest,
                    current_digest=evidence.event_digest,
                )
                raise ValueError(
                    "idempotency collision: the same event identity was reused with "
                    "different event content"
                )
            return AdapterObservation(
                event=event,
                evidence=prior_evidence,
                accepted=False,
                duplicate=True,
            )

        self._persist_seen(key, evidence)
        self._seen[key] = (evidence.event_digest, evidence)
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
