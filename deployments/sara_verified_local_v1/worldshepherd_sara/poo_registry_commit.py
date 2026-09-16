from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .event_outbox import EventOutboxError, queue_event_outbox_patch
from .limits import validate_json_resource
from .poo_audit_adapter import PoOAuditAdapterError, poo_decision_digest


POO_TECHNICAL_REGISTRY_KEY = "POO_TECHNICAL_REGISTRY"
POO_SARA_REGISTRY_SCHEMA = "WS-POO-SARA-TECHNICAL-REGISTRY-V1"
POO_REGISTRY_SCHEMA = "WS-POO-TECHNICAL-REGISTRY-V1"
POO_STATE_SCHEMA = "WS-POO-TECHNICAL-STATE-V1"
POO_DURABLE_COMMIT_REQUEST_SCHEMA = "WS-POO-DURABLE-COMMIT-REQUEST-V1"
POO_DURABLE_COMMIT_RECORD_SCHEMA = "WS-POO-DURABLE-COMMIT-RECORD-V1"
POO_AUDIT_SCHEMA = "WS-POO-GOVERNANCE-DECISION-V3"
POO_BOOTSTRAP_AUDIT_SCHEMA = "WS-POO-BOOTSTRAP-COMMIT-DECISION-V1"
POO_APPROVAL_INTENT = "COMMIT_INTERNAL_TECHNICAL_STATE"
POO_CLAIM_BOUNDARY = "INTERNAL_POO_EVIDENCE_NOT_LEGAL_TITLE_OR_EXECUTION_AUTHORITY"
POO_BOOTSTRAP_CLAIM_BOUNDARY = "INTERNAL_POO_EMPTY_REGISTRY_BOOTSTRAP_ONLY"
MAX_POO_STATES = 32
MAX_POO_COMMIT_RECORDS = 32


class PoODurableCommitError(ValueError):
    pass


class PoOTechnicalStateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_STATE_SCHEMA] = POO_STATE_SCHEMA
    asset_id: str = Field(min_length=1, max_length=256)
    claimant_id: str = Field(min_length=1, max_length=256)
    active_poo_digest: str = Field(min_length=1, max_length=256)
    active_coc_digest: str = Field(min_length=1, max_length=256)
    control_key_fingerprint: str = Field(min_length=1, max_length=512)
    title_reference: str = Field(min_length=1, max_length=512)
    generation: int = Field(ge=0, le=1_000_000)
    source_event_type: Literal["CLAIM", "TRANSFER", "RECOVERY"]
    previous_poo_digest: str | None = Field(default=None, max_length=256)
    previous_coc_digest: str | None = Field(default=None, max_length=256)
    legal_title_established: Literal[False] = False
    live_value_authorized: Literal[False] = False
    external_transfer_executed: Literal[False] = False

    @field_validator("previous_poo_digest", "previous_coc_digest")
    @classmethod
    def optional_digest_nonempty(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("predecessor digest must be null or non-empty")
        return value


class PoOV3CommitReadinessProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_AUDIT_SCHEMA]
    operation: Literal["REGISTRY_COMMIT_READINESS"]
    asset_id: str = Field(min_length=1, max_length=256)
    source_digest: str = Field(min_length=1, max_length=256)
    source_status: Literal["REGISTRY_COMMIT_READY_WITH_FULL_GOVERNANCE"]
    previous_poo_digest: str = Field(min_length=1, max_length=256)
    echo_state: Literal["ECHO_POO_REGISTRY_COMMIT_EVIDENCE_ACCEPTED"]
    prime_state: Literal["PRIME_POO_REGISTRY_COMMIT_CANDIDATE_READY"]
    sara_state: Literal["SARA_POO_REGISTRY_COMMIT_HUMAN_REVIEW_READY"]
    overwatch_state: Literal["OVERWATCH_POO_REGISTRY_COMMIT_PENDING"]
    technical_attestation_ready: Literal[False]
    coc_valid: Literal[False]
    transfer_ready: Literal[False]
    recovery_ready: Literal[False]
    state_transition_ready: Literal[False]
    registry_consistent: Literal[False]
    state_lineage_checked: Literal[True]
    state_lineage_valid: Literal[True]
    poo_lineage_valid: Literal[True]
    coc_lineage_valid: Literal[True]
    generation_valid: Literal[True]
    fork_detected: Literal[False]
    cycle_detected: Literal[False]
    active_tip_digest: str = Field(min_length=1, max_length=256)
    lineage_issue_count: Literal[0]
    registry_commit_ready: Literal[True]
    optimistic_concurrency_checked: Literal[True]
    optimistic_concurrency_match: Literal[True]
    expected_registry_digest: str = Field(min_length=1, max_length=256)
    current_registry_digest: str = Field(min_length=1, max_length=256)
    candidate_registry_digest: str = Field(min_length=1, max_length=256)
    candidate_state_digest: str = Field(min_length=1, max_length=256)
    human_approval_required: Literal[True]
    ownership_changed: Literal[False]
    transfer_executed: Literal[False]
    live_value_authorized: Literal[False]
    legal_title_established: Literal[False]
    legal_title_transferred: Literal[False]
    control_rotated: Literal[False]
    technical_registry_committed: Literal[False]
    durable_registry_write_authorized: Literal[False]
    conflict_winner_selected: Literal[False]
    lineage_auto_resolved: Literal[False]
    claim_boundary: Literal[POO_CLAIM_BOUNDARY]


class PoOBootstrapCommitReadinessProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_BOOTSTRAP_AUDIT_SCHEMA]
    operation: Literal["REGISTRY_BOOTSTRAP_COMMIT_READINESS"]
    asset_id: str = Field(min_length=1, max_length=256)
    source_digest: str = Field(min_length=1, max_length=256)
    source_status: Literal["REGISTRY_BOOTSTRAP_COMMIT_READY_WITH_FULL_GOVERNANCE"]
    echo_state: Literal["ECHO_POO_BOOTSTRAP_EVIDENCE_ACCEPTED"]
    prime_state: Literal["PRIME_POO_BOOTSTRAP_COMMIT_CANDIDATE_READY"]
    sara_state: Literal["SARA_POO_BOOTSTRAP_HUMAN_REVIEW_READY"]
    overwatch_state: Literal["OVERWATCH_POO_BOOTSTRAP_PENDING"]
    empty_registry_verified: Literal[True]
    ownership_evidence_ready: Literal[True]
    coc_valid: Literal[True]
    state_transition_ready: Literal[True]
    registry_commit_ready: Literal[True]
    optimistic_concurrency_checked: Literal[True]
    optimistic_concurrency_match: Literal[True]
    expected_registry_digest: str = Field(min_length=1, max_length=256)
    current_registry_digest: str = Field(min_length=1, max_length=256)
    candidate_registry_digest: str = Field(min_length=1, max_length=256)
    candidate_state_digest: str = Field(min_length=1, max_length=256)
    human_approval_required: Literal[True]
    technical_registry_committed: Literal[False]
    durable_registry_write_authorized: Literal[False]
    legal_title_established: Literal[False]
    legal_title_changed: Literal[False]
    live_value_moved: Literal[False]
    credential_rotated: Literal[False]
    external_transfer_executed: Literal[False]
    claim_boundary: Literal[POO_BOOTSTRAP_CLAIM_BOUNDARY]


class PoODurableCommitRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_DURABLE_COMMIT_RECORD_SCHEMA] = POO_DURABLE_COMMIT_RECORD_SCHEMA
    commit_id: str = Field(min_length=1, max_length=128)
    projection_digest: str = Field(min_length=1, max_length=256)
    source_decision_digest: str = Field(min_length=1, max_length=256)
    previous_registry_digest: str = Field(min_length=1, max_length=256)
    registry_digest: str = Field(min_length=1, max_length=256)
    candidate_state_digest: str = Field(min_length=1, max_length=256)
    approval_reference: str = Field(min_length=1, max_length=256)
    approved_actor: str = Field(min_length=1, max_length=64)
    committed_at: str = Field(min_length=1, max_length=64)
    audit_event_id: str = Field(min_length=1, max_length=160)
    legal_title_changed: Literal[False] = False
    live_value_moved: Literal[False] = False
    credential_rotated: Literal[False] = False
    external_transfer_executed: Literal[False] = False


class PoOTechnicalRegistryNamespace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_SARA_REGISTRY_SCHEMA] = POO_SARA_REGISTRY_SCHEMA
    registry_schema: Literal[POO_REGISTRY_SCHEMA] = POO_REGISTRY_SCHEMA
    registry_digest: str = Field(min_length=1, max_length=256)
    states: list[PoOTechnicalStateRecord] = Field(default_factory=list, max_length=MAX_POO_STATES)
    commits: dict[str, PoODurableCommitRecord] = Field(default_factory=dict)


class PoODurableCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[POO_DURABLE_COMMIT_REQUEST_SCHEMA] = POO_DURABLE_COMMIT_REQUEST_SCHEMA
    governance_projection: PoOV3CommitReadinessProjection | PoOBootstrapCommitReadinessProjection
    candidate_states: list[PoOTechnicalStateRecord] = Field(min_length=1, max_length=MAX_POO_STATES)
    approval_intent: Literal[POO_APPROVAL_INTENT]
    approval_reference: str = Field(min_length=1, max_length=256)


class PoODurableCommitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["COMMITTED", "ALREADY_COMMITTED"]
    commit_id: str
    registry_digest: str
    candidate_state_digest: str
    projection_digest: str
    audit_event_id: str
    approval_reference: str
    approved_actor: str
    durable_internal_state_committed: Literal[True] = True
    legal_title_changed: Literal[False] = False
    live_value_moved: Literal[False] = False
    credential_rotated: Literal[False] = False
    external_transfer_executed: Literal[False] = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_payload(state: PoOTechnicalStateRecord) -> dict[str, Any]:
    return state.model_dump(mode="json")


def poo_state_digest(state: PoOTechnicalStateRecord) -> str:
    raw = json.dumps(
        _state_payload(state),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def poo_registry_digest(states: list[PoOTechnicalStateRecord]) -> str:
    canonical = [_state_payload(state) for state in states]
    canonical.sort(
        key=lambda item: (
            str(item["asset_id"]),
            int(item["generation"]),
            str(item["active_poo_digest"]),
        )
    )
    raw = json.dumps(
        {"schema": POO_REGISTRY_SCHEMA, "states": canonical},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_internal_registry_structure(states: list[PoOTechnicalStateRecord]) -> None:
    poo_digests = [state.active_poo_digest for state in states]
    if len(poo_digests) != len(set(poo_digests)):
        raise PoODurableCommitError("PoO digest reused across durable technical states")

    grouped: dict[str, list[PoOTechnicalStateRecord]] = {}
    for state in states:
        grouped.setdefault(state.asset_id, []).append(state)

    for asset_id, asset_states in grouped.items():
        coc_digests = [state.active_coc_digest for state in asset_states]
        if len(coc_digests) != len(set(coc_digests)):
            raise PoODurableCommitError(f"{asset_id}: COC digest reused across durable states")

        by_poo = {state.active_poo_digest: state for state in asset_states}
        genesis = [state for state in asset_states if state.previous_poo_digest is None]
        if len(genesis) != 1:
            raise PoODurableCommitError(f"{asset_id}: durable lineage requires exactly one genesis")
        root = genesis[0]
        if root.source_event_type != "CLAIM":
            raise PoODurableCommitError(f"{asset_id}: durable genesis must be a CLAIM")
        if root.generation != 0:
            raise PoODurableCommitError(f"{asset_id}: durable genesis generation must be zero")
        if root.previous_coc_digest is not None:
            raise PoODurableCommitError(f"{asset_id}: durable genesis must have no previous COC")

        children: dict[str, list[PoOTechnicalStateRecord]] = {}
        for state in asset_states:
            if state.active_poo_digest == root.active_poo_digest:
                continue
            previous = state.previous_poo_digest
            if previous is None:
                raise PoODurableCommitError(f"{asset_id}: non-genesis state is missing PoO predecessor")
            parent = by_poo.get(previous)
            if parent is None:
                raise PoODurableCommitError(f"{asset_id}: durable PoO predecessor is missing")
            if state.previous_coc_digest != parent.active_coc_digest:
                raise PoODurableCommitError(f"{asset_id}: durable COC predecessor mismatch")
            if state.generation != parent.generation + 1:
                raise PoODurableCommitError(f"{asset_id}: durable generation does not advance parent by one")
            if state.source_event_type == "CLAIM":
                raise PoODurableCommitError(f"{asset_id}: CLAIM is only valid for genesis")
            children.setdefault(previous, []).append(state)

        if any(len(items) > 1 for items in children.values()):
            raise PoODurableCommitError(f"{asset_id}: durable technical lineage fork detected")

        visited: set[str] = set()
        cursor = root
        while True:
            digest = cursor.active_poo_digest
            if digest in visited:
                raise PoODurableCommitError(f"{asset_id}: durable technical lineage cycle detected")
            visited.add(digest)
            next_states = children.get(digest, [])
            if not next_states:
                break
            cursor = next_states[0]

        if len(visited) != len(asset_states):
            raise PoODurableCommitError(f"{asset_id}: durable technical lineage is disconnected or cyclic")


def _new_namespace() -> PoOTechnicalRegistryNamespace:
    return PoOTechnicalRegistryNamespace(
        registry_digest=poo_registry_digest([]),
        states=[],
        commits={},
    )


def load_poo_registry_namespace(registry: dict[str, Any]) -> PoOTechnicalRegistryNamespace:
    raw = registry.get(POO_TECHNICAL_REGISTRY_KEY)
    if raw is None:
        return _new_namespace()
    if not isinstance(raw, dict):
        raise PoODurableCommitError(f"{POO_TECHNICAL_REGISTRY_KEY} must be a JSON object")
    try:
        namespace = PoOTechnicalRegistryNamespace.model_validate(raw)
    except ValueError as exc:
        raise PoODurableCommitError("PoO technical registry namespace is malformed") from exc

    recomputed = poo_registry_digest(namespace.states)
    if namespace.registry_digest != recomputed:
        raise PoODurableCommitError("PoO technical registry digest does not match stored states")

    state_digests = [poo_state_digest(state) for state in namespace.states]
    if len(state_digests) != len(set(state_digests)):
        raise PoODurableCommitError("PoO technical registry contains duplicate states")
    _validate_internal_registry_structure(namespace.states)

    if len(namespace.commits) > MAX_POO_COMMIT_RECORDS:
        raise PoODurableCommitError("PoO commit record capacity exceeded")
    for commit_id, record in namespace.commits.items():
        if commit_id != record.commit_id:
            raise PoODurableCommitError("PoO commit record key does not match commit_id")
    return namespace


def _canonical_projection_digest(projection: dict[str, Any]) -> str:
    raw = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _validate_bootstrap_projection(projection: dict[str, Any]) -> str:
    if projection["expected_registry_digest"] != projection["current_registry_digest"]:
        raise PoODurableCommitError("bootstrap projection snapshot digests disagree")
    return _canonical_projection_digest(projection)


def _validated_ready_projection(projection: dict[str, Any]) -> str:
    if projection.get("schema") == POO_BOOTSTRAP_AUDIT_SCHEMA:
        return _validate_bootstrap_projection(projection)

    try:
        return poo_decision_digest(projection)
    except PoOAuditAdapterError as exc:
        raise PoODurableCommitError("invalid PoO governance projection") from exc


def _deterministic_commit_id(projection: dict[str, Any], projection_digest: str) -> str:
    payload = {
        "schema": POO_DURABLE_COMMIT_RECORD_SCHEMA,
        "projection_digest": projection_digest,
        "source_decision_digest": projection["source_digest"],
        "candidate_registry_digest": projection["candidate_registry_digest"],
        "candidate_state_digest": projection["candidate_state_digest"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "POO-COMMIT-" + hashlib.sha256(raw).hexdigest()[:32]


def _result_from_record(
    record: PoODurableCommitRecord,
    *,
    status: Literal["COMMITTED", "ALREADY_COMMITTED"],
) -> PoODurableCommitResult:
    return PoODurableCommitResult(
        status=status,
        commit_id=record.commit_id,
        registry_digest=record.registry_digest,
        candidate_state_digest=record.candidate_state_digest,
        projection_digest=record.projection_digest,
        audit_event_id=record.audit_event_id,
        approval_reference=record.approval_reference,
        approved_actor=record.approved_actor,
    )


def prepare_poo_durable_commit_patch(
    registry: dict[str, Any],
    request: PoODurableCommitRequest,
    *,
    actor: str,
    committed_at: str | None = None,
) -> tuple[dict[str, Any] | None, PoODurableCommitResult]:
    if not actor:
        raise PoODurableCommitError("approved actor must be non-empty")

    projection = request.governance_projection.model_dump(mode="json")
    projection_digest = _validated_ready_projection(projection)
    commit_id = _deterministic_commit_id(projection, projection_digest)
    audit_event_id = f"SARA-EVENT-{commit_id}"
    namespace = load_poo_registry_namespace(registry)

    candidate_states = list(request.candidate_states)
    candidate_registry_digest = poo_registry_digest(candidate_states)
    if candidate_registry_digest != projection["candidate_registry_digest"]:
        raise PoODurableCommitError("candidate states do not match governance candidate registry digest")
    _validate_internal_registry_structure(candidate_states)

    candidate_state_digest = projection["candidate_state_digest"]

    existing = namespace.commits.get(commit_id)
    if existing is not None:
        if (
            existing.projection_digest != projection_digest
            or existing.registry_digest != candidate_registry_digest
            or existing.candidate_state_digest != candidate_state_digest
        ):
            raise PoODurableCommitError("commit_id collision with different PoO commit material")
        current_state_digests = {poo_state_digest(state) for state in namespace.states}
        if existing.candidate_state_digest not in current_state_digests:
            raise PoODurableCommitError("recorded PoO commit candidate state is missing from active registry")
        return None, _result_from_record(existing, status="ALREADY_COMMITTED")

    expected_registry_digest = projection["expected_registry_digest"]
    projected_current_digest = projection["current_registry_digest"]
    if expected_registry_digest != projected_current_digest:
        raise PoODurableCommitError("governance projection snapshot digests disagree")
    if namespace.registry_digest != expected_registry_digest:
        raise PoODurableCommitError("stale PoO registry snapshot; governance reevaluation required")

    if len(namespace.commits) >= MAX_POO_COMMIT_RECORDS:
        raise PoODurableCommitError("PoO commit record capacity reached")
    if len(candidate_states) != len(namespace.states) + 1:
        raise PoODurableCommitError("candidate registry must extend current registry by exactly one state")

    current_digests = {poo_state_digest(state) for state in namespace.states}
    candidate_digests = {poo_state_digest(state) for state in candidate_states}
    if len(candidate_digests) != len(candidate_states):
        raise PoODurableCommitError("candidate registry contains duplicate states")
    if not current_digests.issubset(candidate_digests):
        raise PoODurableCommitError("candidate registry modifies or removes existing technical states")
    added = candidate_digests.difference(current_digests)
    if added != {candidate_state_digest}:
        raise PoODurableCommitError("candidate registry does not add exactly the governed candidate state")

    commit_record = PoODurableCommitRecord(
        commit_id=commit_id,
        projection_digest=projection_digest,
        source_decision_digest=projection["source_digest"],
        previous_registry_digest=namespace.registry_digest,
        registry_digest=candidate_registry_digest,
        candidate_state_digest=candidate_state_digest,
        approval_reference=request.approval_reference,
        approved_actor=actor,
        committed_at=committed_at or _utc_now(),
        audit_event_id=audit_event_id,
    )
    commits = dict(namespace.commits)
    commits[commit_id] = commit_record
    updated_namespace = PoOTechnicalRegistryNamespace(
        registry_digest=candidate_registry_digest,
        states=candidate_states,
        commits=commits,
    )
    namespace_payload = updated_namespace.model_dump(mode="json")
    validate_json_resource(namespace_payload)

    base_patch = {POO_TECHNICAL_REGISTRY_KEY: namespace_payload}
    working = dict(registry)
    working.update(base_patch)
    event_patch, event_id = queue_event_outbox_patch(
        working,
        event="poo_technical_registry_committed",
        actor=actor,
        event_id=audit_event_id,
        payload={
            "commit_id": commit_id,
            "projection_schema": projection["schema"],
            "projection_digest": projection_digest,
            "source_decision_digest": projection["source_digest"],
            "approval_reference": request.approval_reference,
            "previous_registry_digest": namespace.registry_digest,
            "registry_digest": candidate_registry_digest,
            "candidate_state_digest": candidate_state_digest,
            "durable_internal_state_committed": True,
            "legal_title_changed": False,
            "live_value_moved": False,
            "credential_rotated": False,
            "external_transfer_executed": False,
            "claims_boundary": "INTERNAL_TECHNICAL_REGISTRY_COMMIT_ONLY",
        },
    )
    if event_id != audit_event_id:
        raise EventOutboxError("PoO audit event ID changed unexpectedly")

    patch = dict(base_patch)
    patch.update(event_patch)
    return patch, _result_from_record(commit_record, status="COMMITTED")
