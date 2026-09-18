from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import AuditRecord
from .prime_sentinel_authorization import PrimeSentinelAuthorizationError
from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode, canonical_digest
from .sda_identity import VerifiedSdaWorkloadIdentity, assert_workload_identity_bound_to_adapter


SDA_OBSERVATION_SCHEMA = "WS-SDA-OBSERVATION-V1"
SDA_FUSION_SCHEMA = "WS-SDA-FUSED-HYPOTHESIS-V1"
SDA_GATE_EVENT = "sda_observation_gate"
SDA_GATE_ACTOR = "SDA_GATEWAY"


class SdaSourceClass(str, Enum):
    GOVERNMENT = "GOVERNMENT"
    ALLIED = "ALLIED"
    COMMERCIAL = "COMMERCIAL"
    PUBLIC = "PUBLIC"
    SYNTHETIC = "SYNTHETIC"


class SdaContractValidationState(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    INTERNAL = "INTERNAL"
    PARTNER_VALIDATED = "PARTNER_VALIDATED"


class SdaIngestDisposition(str, Enum):
    ACCEPT = "ACCEPT"
    DUPLICATE = "DUPLICATE"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"


class SdaSourceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=128)
    source_class: SdaSourceClass
    provider: str = Field(min_length=1, max_length=256)
    sensor_id: str = Field(min_length=1, max_length=128)
    adapter_id: str = Field(min_length=1, max_length=128)
    adapter_version: str = Field(min_length=1, max_length=64)


class SdaInterfaceContract(BaseModel):
    """Explicit allow-list for one source/adapter boundary.

    Enabled means the software contract may be exercised in the stated validation
    state. It does not imply government, partner, UDL, CCSDS, or operational acceptance.
    """

    model_config = ConfigDict(extra="forbid")

    contract_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128)
    adapter_id: str = Field(min_length=1, max_length=128)
    adapter_version: str = Field(min_length=1, max_length=64)
    authoritative_spec_ref: str = Field(min_length=1, max_length=512)
    authoritative_spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    allowed_reference_frames: list[str] = Field(min_length=1, max_length=32)
    allowed_releasability_tags: list[str] = Field(default_factory=list, max_length=64)
    max_age_seconds: float = Field(gt=0.0, le=86400.0)
    max_future_skew_seconds: float = Field(ge=0.0, le=300.0, default=60.0)
    max_clock_uncertainty_seconds: float = Field(gt=0.0, le=3600.0)
    validation_state: SdaContractValidationState = SdaContractValidationState.SYNTHETIC
    validation_ref: str | None = Field(default=None, max_length=512)
    require_workload_identity: bool = False
    enabled: bool = False

    @field_validator("allowed_reference_frames", "allowed_releasability_tags")
    @classmethod
    def values_are_unique_and_bounded(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item or len(item) > 128 for item in cleaned):
            raise ValueError("contract list values must contain 1-128 characters")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("contract list values must be unique")
        return cleaned

    @model_validator(mode="after")
    def enabled_contract_requires_validation_ref(self) -> "SdaInterfaceContract":
        if self.enabled and not self.validation_ref:
            raise ValueError("enabled SDA interface contract requires validation_ref")
        return self

    def digest(self) -> str:
        return canonical_digest(self)


class SdaObservation(BaseModel):
    """Canonical state-vector observation with bounded provenance metadata.

    This is an interoperability/evidence contract, not an operational orbit
    determination result or a validated space surveillance message profile.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[SDA_OBSERVATION_SCHEMA] = SDA_OBSERVATION_SCHEMA
    observation_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    source_event_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    source_sequence: int = Field(ge=0)
    source: SdaSourceIdentity

    observed_at: datetime
    received_at: datetime
    time_system: str = Field(min_length=1, max_length=32)
    clock_uncertainty_seconds: float = Field(ge=0.0, le=3600.0)

    reference_frame: str = Field(min_length=1, max_length=64)
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    covariance_6x6: list[list[float]]

    measurement_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_reliability: float | None = Field(default=None, ge=0.0, le=1.0)

    handling_label: str = Field(default="UNCLASSIFIED_SYNTHETIC", min_length=1, max_length=128)
    releasability_tags: list[str] = Field(default_factory=list, max_length=64)

    raw_source_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    interface_contract_id: str = Field(min_length=1, max_length=128)
    interface_contract_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    transformation_refs: list[str] = Field(default_factory=list, max_length=128)
    source_signature_ref: str | None = Field(default=None, max_length=512)

    @field_validator("observed_at", "received_at")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("SDA timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("position_km", "velocity_km_s")
    @classmethod
    def vectors_are_finite(cls, value: tuple[float, float, float]) -> tuple[float, float, float]:
        if not all(isfinite(item) for item in value):
            raise ValueError("state-vector components must be finite")
        return value

    @field_validator("covariance_6x6")
    @classmethod
    def covariance_is_bounded_symmetric_and_positive_diagonal(
        cls, value: list[list[float]]
    ) -> list[list[float]]:
        if len(value) != 6 or any(len(row) != 6 for row in value):
            raise ValueError("covariance_6x6 must be exactly 6x6")
        if any(not isfinite(item) for row in value for item in row):
            raise ValueError("covariance values must be finite")
        for index in range(6):
            if value[index][index] <= 0.0:
                raise ValueError("covariance diagonal must be strictly positive")
            for other in range(6):
                scale = max(1.0, abs(value[index][other]), abs(value[other][index]))
                if abs(value[index][other] - value[other][index]) > 1e-12 * scale:
                    raise ValueError("covariance_6x6 must be symmetric")
        return value

    @field_validator("releasability_tags", "transformation_refs")
    @classmethod
    def list_values_are_unique_and_bounded(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item or len(item) > 256 for item in cleaned):
            raise ValueError("SDA list values must contain 1-256 characters")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("SDA list values must be unique")
        return cleaned

    def semantic_digest(self) -> str:
        return canonical_digest(self)

    def stable_event_id(self) -> str:
        identity = {
            "schema": self.schema,
            "source_id": self.source.source_id,
            "source_event_id": self.source_event_id,
            "source_sequence": self.source_sequence,
        }
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "SARA-EVENT-SDA-" + hashlib.sha256(encoded).hexdigest()


class SdaReplayState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=128)
    last_sequence: int = Field(ge=0)
    last_event_id: str = Field(min_length=1, max_length=128)
    last_semantic_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class SdaIngestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: SdaIngestDisposition
    reasons: list[str] = Field(default_factory=list)
    event_id: str = Field(min_length=1)
    semantic_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    next_replay_state: SdaReplayState | None = None


def evaluate_sda_ingest(
    observation: SdaObservation,
    *,
    contract: SdaInterfaceContract,
    replay_state: SdaReplayState | None = None,
    workload_identity: VerifiedSdaWorkloadIdentity | None = None,
    now: datetime | None = None,
) -> SdaIngestResult:
    """Fail closed at the source-isolation boundary.

    Rejected messages fail identity/contract/replay invariants.
    Quarantined messages are structurally valid but outside freshness, timing,
    frame, or releasability policy and require policy/human disposition.
    """

    event_id = observation.stable_event_id()
    digest = observation.semantic_digest()
    reject: list[str] = []
    quarantine: list[str] = []
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    if not contract.enabled:
        reject.append("interface contract is disabled")
    if observation.source.source_id != contract.source_id:
        reject.append("source identity does not match interface contract")
    if observation.source.adapter_id != contract.adapter_id:
        reject.append("adapter identity does not match interface contract")
    if observation.source.adapter_version != contract.adapter_version:
        reject.append("adapter version does not match interface contract")
    if observation.interface_contract_id != contract.contract_id:
        reject.append("observation interface_contract_id does not match active contract")
    if observation.interface_contract_digest != contract.digest():
        reject.append("observation interface contract digest is stale or mismatched")

    if contract.require_workload_identity:
        if workload_identity is None:
            reject.append("active interface contract requires verified workload identity")
        else:
            try:
                assert_workload_identity_bound_to_adapter(
                    workload_identity,
                    source_id=observation.source.source_id,
                    adapter_id=observation.source.adapter_id,
                    adapter_version=observation.source.adapter_version,
                    now=current,
                )
                if contract.require_transport_identity:
                    if transport_identity is None:
                        reject.append(
                            "active interface contract requires verified mTLS transport identity"
                        )
                    else:
                        assert_transport_identity_bound_to_workload(
                            transport_identity,
                            workload_identity,
                            now=current,
                        )
            except PrimeSentinelAuthorizationError as exc:
                reject.append(f"workload or transport identity rejected: {exc}")

    if replay_state is not None:
        if replay_state.source_id != observation.source.source_id:
            reject.append("replay state belongs to a different source")
        elif observation.source_sequence < replay_state.last_sequence:
            reject.append("source sequence moved backwards")
        elif observation.source_sequence == replay_state.last_sequence:
            same_event = observation.source_event_id == replay_state.last_event_id
            same_content = digest == replay_state.last_semantic_digest
            if same_event and same_content and not reject:
                return SdaIngestResult(
                    disposition=SdaIngestDisposition.DUPLICATE,
                    reasons=["exact duplicate of the last accepted source event"],
                    event_id=event_id,
                    semantic_digest=digest,
                    next_replay_state=replay_state,
                )
            reject.append("source sequence collision or mutated replay detected")

    if observation.reference_frame not in contract.allowed_reference_frames:
        quarantine.append("reference frame is outside the active contract allow-list")

    allowed_tags = set(contract.allowed_releasability_tags)
    observed_tags = set(observation.releasability_tags)
    if observed_tags - allowed_tags:
        quarantine.append("observation releasability tags exceed active contract")

    observed = observation.observed_at.astimezone(timezone.utc)
    if observed > current:
        future_skew = (observed - current).total_seconds()
        if future_skew > contract.max_future_skew_seconds:
            quarantine.append("observation timestamp exceeds future-skew allowance")
    else:
        age = (current - observed).total_seconds()
        if age > contract.max_age_seconds:
            quarantine.append("observation is stale under the active contract")

    if observation.clock_uncertainty_seconds > contract.max_clock_uncertainty_seconds:
        quarantine.append("clock uncertainty exceeds active contract")

    if reject:
        return SdaIngestResult(
            disposition=SdaIngestDisposition.REJECT,
            reasons=reject,
            event_id=event_id,
            semantic_digest=digest,
        )

    if quarantine:
        return SdaIngestResult(
            disposition=SdaIngestDisposition.QUARANTINE,
            reasons=quarantine,
            event_id=event_id,
            semantic_digest=digest,
        )

    next_state = SdaReplayState(
        source_id=observation.source.source_id,
        last_sequence=observation.source_sequence,
        last_event_id=observation.source_event_id,
        last_semantic_digest=digest,
    )
    return SdaIngestResult(
        disposition=SdaIngestDisposition.ACCEPT,
        reasons=["source, contract, workload identity when required, replay, timing, frame, and releasability gates passed"],
        event_id=event_id,
        semantic_digest=digest,
        next_replay_state=next_state,
    )


def sda_audit_record(
    observation: SdaObservation,
    result: SdaIngestResult,
    *,
    audit_timestamp: datetime | None = None,
) -> AuditRecord:
    timestamp = (audit_timestamp or observation.received_at).astimezone(timezone.utc)
    return AuditRecord(
        timestamp=timestamp.isoformat().replace("+00:00", "Z"),
        event=SDA_GATE_EVENT,
        actor=SDA_GATE_ACTOR,
        payload={
            "_outbox_event_id": result.event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "schema": SDA_OBSERVATION_SCHEMA,
            "disposition": result.disposition.value,
            "reasons": list(result.reasons),
            "semantic_digest": result.semantic_digest,
            "observation": observation.model_dump(mode="json"),
            "raw_source_persisted": False,
            "claims_boundary": (
                "Canonical SDA software evidence only; no operational orbit determination, "
                "government acceptance, partner acceptance, or classified-network authorization is claimed."
            ),
        },
    )


class SdaFusionConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_observation_id: str
    right_observation_id: str
    normalized_residual_score: float = Field(ge=0.0)
    threshold: float = Field(gt=0.0)


class SdaFusedHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[SDA_FUSION_SCHEMA] = SDA_FUSION_SCHEMA
    hypothesis_id: str = Field(pattern=r"^SDA-FUSED-[0-9a-f]{16}$")
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    covariance_6x6: list[list[float]]
    source_observation_ids: list[str] = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    conflicts: list[SdaFusionConflict] = Field(default_factory=list)
    scope_note: str = (
        "Deterministic diagonal inverse-variance synthetic/reference fusion only; "
        "not JPDA/MHT, orbit determination, maneuver detection, or operational SDA tracking."
    )


def _state_components(observation: SdaObservation) -> tuple[float, ...]:
    return (*observation.position_km, *observation.velocity_km_s)


def _pairwise_residual_score(left: SdaObservation, right: SdaObservation) -> float:
    left_state = _state_components(left)
    right_state = _state_components(right)
    score = 0.0
    for index in range(6):
        variance = left.covariance_6x6[index][index] + right.covariance_6x6[index][index]
        delta = left_state[index] - right_state[index]
        score += (delta * delta) / variance
    return score


def fuse_sda_state_vectors(
    observations: list[SdaObservation],
    *,
    conflict_threshold: float = 36.0,
) -> SdaFusedHypothesis:
    """Fuse a bounded set using only declared measurement variances.

    measurement_confidence and source_reliability are deliberately not numerical
    fusion weights. They remain separate governance/quality signals.
    """

    if not observations:
        raise ValueError("at least one SDA observation is required for fusion")
    if conflict_threshold <= 0.0:
        raise ValueError("conflict_threshold must be positive")

    frames = {item.reference_frame for item in observations}
    if len(frames) != 1:
        raise ValueError("all observations must use the same reference frame")
    epochs = {item.observed_at for item in observations}
    if len(epochs) != 1:
        raise ValueError("v1 fusion requires an identical observation epoch")

    fused: list[float] = []
    variances: list[float] = []
    for index in range(6):
        weights = [1.0 / item.covariance_6x6[index][index] for item in observations]
        total = sum(weights)
        values = [_state_components(item)[index] for item in observations]
        fused.append(sum(value * weight for value, weight in zip(values, weights)) / total)
        variances.append(1.0 / total)

    covariance = [[0.0 for _ in range(6)] for _ in range(6)]
    for index, variance in enumerate(variances):
        covariance[index][index] = variance

    conflicts: list[SdaFusionConflict] = []
    ordered = sorted(observations, key=lambda item: item.observation_id)
    for left_index, left in enumerate(ordered):
        for right in ordered[left_index + 1 :]:
            score = _pairwise_residual_score(left, right)
            if score > conflict_threshold:
                conflicts.append(
                    SdaFusionConflict(
                        left_observation_id=left.observation_id,
                        right_observation_id=right.observation_id,
                        normalized_residual_score=score,
                        threshold=conflict_threshold,
                    )
                )

    identity_payload = {
        "observations": [item.observation_id for item in ordered],
        "digests": [item.semantic_digest() for item in ordered],
        "position_km": fused[:3],
        "velocity_km_s": fused[3:],
        "covariance_6x6": covariance,
    }
    suffix = canonical_digest(identity_payload).split(":", 1)[1][:16]

    return SdaFusedHypothesis(
        hypothesis_id=f"SDA-FUSED-{suffix}",
        position_km=(fused[0], fused[1], fused[2]),
        velocity_km_s=(fused[3], fused[4], fused[5]),
        covariance_6x6=covariance,
        source_observation_ids=[item.observation_id for item in ordered],
        source_ids=sorted({item.source.source_id for item in ordered}),
        conflicts=conflicts,
    )


def sda_fusion_evidence_graph(
    *,
    graph_id: str,
    observations: list[SdaObservation],
    hypothesis: SdaFusedHypothesis,
) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []

    by_id = {item.observation_id: item for item in observations}
    for observation in observations:
        nodes.append(
            EvidenceGraphNode(
                node_id=f"sda-observation:{observation.observation_id}",
                node_type="sda_observation",
                label=observation.observation_id,
                source_ref=f"source:{observation.source.source_id}",
                confidence=observation.measurement_confidence,
                attributes={
                    "semantic_digest": observation.semantic_digest(),
                    "source_id": observation.source.source_id,
                    "source_class": observation.source.source_class.value,
                    "reference_frame": observation.reference_frame,
                    "clock_uncertainty_seconds": observation.clock_uncertainty_seconds,
                    "source_reliability": observation.source_reliability,
                },
            )
        )

    nodes.append(
        EvidenceGraphNode(
            node_id=f"sda-hypothesis:{hypothesis.hypothesis_id}",
            node_type="sda_fused_hypothesis",
            label=hypothesis.hypothesis_id,
            attributes=hypothesis.model_dump(mode="json"),
        )
    )
    for observation_id in hypothesis.source_observation_ids:
        if observation_id not in by_id:
            raise ValueError("hypothesis references an observation not supplied to graph")
        edges.append(
            EvidenceGraphEdge(
                edge_id=f"sda-support:{observation_id}:{hypothesis.hypothesis_id}",
                source_node_id=f"sda-observation:{observation_id}",
                target_node_id=f"sda-hypothesis:{hypothesis.hypothesis_id}",
                relation="contributes_to",
                source_ref=f"observation:{observation_id}",
                confidence=1.0,
            )
        )

    for index, conflict in enumerate(hypothesis.conflicts, start=1):
        conflict_id = f"sda-conflict:{hypothesis.hypothesis_id}:{index}"
        nodes.append(
            EvidenceGraphNode(
                node_id=conflict_id,
                node_type="sda_fusion_conflict",
                label=f"conflict-{index}",
                attributes=conflict.model_dump(mode="json"),
            )
        )
        for observation_id in (
            conflict.left_observation_id,
            conflict.right_observation_id,
        ):
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"sda-conflict-edge:{index}:{observation_id}",
                    source_node_id=f"sda-observation:{observation_id}",
                    target_node_id=conflict_id,
                    relation="conflicts_in_fusion",
                    source_ref=f"observation:{observation_id}",
                    confidence=1.0,
                )
            )
        edges.append(
            EvidenceGraphEdge(
                edge_id=f"sda-conflict-hypothesis:{index}",
                source_node_id=conflict_id,
                target_node_id=f"sda-hypothesis:{hypothesis.hypothesis_id}",
                relation="qualifies_uncertainty",
                confidence=1.0,
            )
        )

    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)
