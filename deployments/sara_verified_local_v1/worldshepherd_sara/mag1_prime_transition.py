from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from .event_outbox import queue_event_outbox_patch
from .mag1_evidence import (
    build_mag1_evidence_payload,
    mag1_evidence_event_id,
    policy_bundle_sha256,
    queue_mag1_evidence_patch,
)
from .mag1_gate import Mag1Decision, Mag1Disposition
from .mag1_prime_binding import (
    PRIME_MAG1_ACTION,
    PrimeMag1Binding,
    evaluate_prime_requalification_mag1,
)
from .overwatch_containment import (
    OverwatchContainmentStatus,
    OverwatchContainmentVerifier,
    evaluate_overwatch_containment,
)
from .prime_configuration_custody import (
    PrimeActivationDisposition,
    PrimeConfigurationCustodyRecord,
    PrimeCustodyState,
    PrimeMissionPackEvidence,
    release_from_quarantine,
)
from .prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
    consumed_authorization_registry_patch,
)
from .registry_monotonic_witness import RegistryMonotonicWitnessVerifier
from .registry_witness_gate import (
    RegistryWitnessPrecondition,
    assert_registry_witness_precondition,
)
from .storage import DurableStore
from .trajectory_guard import (
    SideEffectClass,
    TrajectoryAction,
    TrajectoryGuardPolicy,
    TrajectoryState,
)


PRIME_CUSTODY_REGISTRY_KEY = "PRIME_CONFIGURATION_CUSTODY"
PRIME_MAG1_TRANSITION_SCHEMA = "WS-PRIME-MAG1-TRANSITION-V1"
PRIME_MAG1_TRANSITION_EVENT = "prime_requalification_transition"
PRIME_MAG1_TRANSITION_ACTOR = "MAG1_PRIME_TRANSITION"
OVERWATCH_CONTAINMENT_BLOCK_SCHEMA = "WS-OVERWATCH-CONTAINMENT-BLOCK-V1"
OVERWATCH_CONTAINMENT_BLOCK_EVENT = "overwatch_containment_block"
OVERWATCH_CONTAINMENT_BLOCK_ACTOR = "OVERWATCH"


class PrimeMag1TransitionError(ValueError):
    pass


class PrimeMag1TransitionDisposition(str, Enum):
    APPLIED = "APPLIED"
    NOT_APPLIED = "NOT_APPLIED"
    CONTAINED = "CONTAINED"


class PrimeMag1TransitionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: PrimeMag1TransitionDisposition
    transition_id: str | None = None
    prime_id: str
    authorization_id: str
    target_environment: str
    mag1_decision: Mag1Decision
    before_custody_sha256: str
    after_custody_sha256: str | None = None
    mag1_event_id: str | None = None
    transition_event_id: str | None = None
    overwatch_containment_event_id: str | None = None
    overwatch_directive_id: str | None = None
    overwatch_directive_sha256: str | None = None
    overwatch_sequence: int = 0
    registry_witness_receipt_sha256: str | None = None
    registry_witness_precondition_sha256: str | None = None
    release_reasons: list[str] = Field(default_factory=list)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def custody_record_sha256(record: PrimeConfigurationCustodyRecord) -> str:
    return _sha256(record.model_dump(mode="json"))


def _custody_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(PRIME_CUSTODY_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise PrimeMag1TransitionError(
            f"{PRIME_CUSTODY_REGISTRY_KEY} must be a JSON object"
        )
    return dict(raw)


def get_prime_custody_record(
    registry: dict[str, Any],
    *,
    prime_id: str,
) -> PrimeConfigurationCustodyRecord:
    records = _custody_map(registry)
    raw = records.get(prime_id)
    if not isinstance(raw, dict):
        raise PrimeMag1TransitionError("PRIME custody record is not registered")
    try:
        record = PrimeConfigurationCustodyRecord.model_validate(raw)
    except ValueError as exc:
        raise PrimeMag1TransitionError("PRIME custody record is malformed") from exc
    if record.prime_id != prime_id:
        raise PrimeMag1TransitionError("PRIME custody registry identity mismatch")
    return record


def prime_custody_registry_patch(
    registry: dict[str, Any],
    record: PrimeConfigurationCustodyRecord,
) -> dict[str, Any]:
    records = _custody_map(registry)
    records[record.prime_id] = record.model_dump(mode="json")
    return {PRIME_CUSTODY_REGISTRY_KEY: records}


def _transition_id(
    *,
    binding: PrimeMag1Binding,
    before_custody_sha256: str,
    pack: PrimeMissionPackEvidence,
    trajectory_id: str,
    action_id: str,
    policy_bundle_hash: str,
    overwatch_snapshot_sha256: str,
    registry_witness_precondition_sha256: str,
) -> str:
    digest = _sha256(
        {
            "schema": PRIME_MAG1_TRANSITION_SCHEMA,
            "authorization_id": binding.verified.authorization_id,
            "prime_id": binding.verified.prime_id,
            "target_environment": binding.verified.target_environment.value,
            "key_id": binding.verified.key_id,
            "before_custody_sha256": before_custody_sha256,
            "pack": pack.model_dump(mode="json"),
            "trajectory_id": trajectory_id,
            "action_id": action_id,
            "policy_bundle_sha256": policy_bundle_hash,
            "overwatch_snapshot_sha256": overwatch_snapshot_sha256,
            "registry_witness_precondition_sha256": registry_witness_precondition_sha256,
        }
    )
    return f"PRIME-MAG1-TRANSITION-{digest}"


def _transition_event_id(transition_id: str) -> str:
    return f"SARA-EVENT-PRIME-TRANSITION-{hashlib.sha256(transition_id.encode('utf-8')).hexdigest()}"


def _containment_event_id(
    *,
    containment: OverwatchContainmentStatus,
    authorization_id: str,
    trajectory_id: str,
    action_id: str,
) -> str:
    if not containment.active or not containment.directive_sha256:
        raise PrimeMag1TransitionError(
            "active OVERWATCH containment must have a directive hash"
        )
    digest = _sha256(
        {
            "schema": OVERWATCH_CONTAINMENT_BLOCK_SCHEMA,
            "directive_sha256": containment.directive_sha256,
            "authorization_id": authorization_id,
            "trajectory_id": trajectory_id,
            "action_id": action_id,
        }
    )
    return f"SARA-EVENT-OVERWATCH-BLOCK-{digest}"


def _assert_release_binding_available_or_matching(
    record: PrimeConfigurationCustodyRecord,
    binding: PrimeMag1Binding,
) -> None:
    expected = {
        "requalification_release_authorization_id": binding.verified.authorization_id,
        "requalification_release_target_environment": binding.verified.target_environment,
        "requalification_release_key_id": binding.verified.key_id,
    }
    for field_name, expected_value in expected.items():
        current = getattr(record, field_name)
        if current is not None and current != expected_value:
            raise PrimeMag1TransitionError(
                f"existing custody {field_name} conflicts with verified PRIME authorization"
            )


def _bind_release_authorization(
    record: PrimeConfigurationCustodyRecord,
    binding: PrimeMag1Binding,
) -> PrimeConfigurationCustodyRecord:
    _assert_release_binding_available_or_matching(record, binding)
    return record.model_copy(
        update={
            "requalification_release_authorization_id": binding.verified.authorization_id,
            "requalification_release_target_environment": binding.verified.target_environment,
            "requalification_release_key_id": binding.verified.key_id,
        }
    )


def execute_prime_requalification_transition(
    store: DurableStore,
    *,
    assertion: PrimeSentinelAuthorizationAssertion,
    verifier: PrimeSentinelVerifier,
    pack: PrimeMissionPackEvidence,
    candidate: AutonomousActionCandidate,
    autonomy_policy: AutonomyPolicy,
    trajectory_state: TrajectoryState,
    trajectory_action_id: str,
    trajectory_policy: TrajectoryGuardPolicy | None = None,
    overwatch_verifier: OverwatchContainmentVerifier | None = None,
    registry_witness_precondition: RegistryWitnessPrecondition | None = None,
    registry_witness_verifier: RegistryMonotonicWitnessVerifier | None = None,
    now: datetime | None = None,
) -> PrimeMag1TransitionResult:
    """Evaluate PRIME requalification and gate every applied release on a signed remote witness.

    Non-applied MAG-1 decisions and active OVERWATCH containment may return
    without a witness because they do not consume authority or release custody.
    Once a transition reaches the consequential release boundary, however, both
    a prepared REMOTE_WITNESS receipt and a pinned-key verifier are mandatory.
    The signed receipt is re-verified locally and its generation/root/commit are
    compared to the storage-owned checkpoint metadata while the registry lock is
    held. There is no caller-selectable opt-out for an APPLIED release.

    The remote head should be fetched and prepared before calling this function.
    No remote network I/O occurs while the registry lock is held. An intervening
    cooperating write changes checkpoint coordinates and makes the precondition
    stale, causing a fail-closed abort before authorization consumption or
    custody release.
    """

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise PrimeMag1TransitionError("now must be timezone-aware")
    current_time = current_time.astimezone(timezone.utc)

    if candidate.action_type != PRIME_MAG1_ACTION:
        raise PrimeMag1TransitionError(
            "candidate action must be REQUALIFICATION_RELEASE"
        )
    if candidate.action_id != trajectory_action_id:
        raise PrimeMag1TransitionError(
            "candidate action_id must match trajectory action_id"
        )

    def operation(registry: dict[str, Any]):
        record = get_prime_custody_record(
            registry,
            prime_id=assertion.prime_id,
        )
        before_hash = custody_record_sha256(record)
        if record.state != PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION:
            raise PrimeMag1TransitionError(
                "PRIME is not quarantined for requalification"
            )

        canonical_action = TrajectoryAction(
            action_id=trajectory_action_id,
            action_type=PRIME_MAG1_ACTION,
            side_effect=SideEffectClass.EXECUTE,
        )
        decision, binding = evaluate_prime_requalification_mag1(
            assertion=assertion,
            verifier=verifier,
            registry=registry,
            candidate=candidate,
            autonomy_policy=autonomy_policy,
            trajectory_state=trajectory_state,
            trajectory_action=canonical_action,
            trajectory_policy=trajectory_policy,
            now=current_time,
        )

        if binding.verified.prime_id != record.prime_id:
            raise PrimeMag1TransitionError(
                "verified PRIME authorization does not match custody identity"
            )
        if binding.verified.target_environment != pack.target_environment:
            raise PrimeMag1TransitionError(
                "verified PRIME target environment does not match mission pack"
            )

        mag1_payload = build_mag1_evidence_payload(
            decision=decision,
            trajectory_action=canonical_action,
            autonomy_policy=autonomy_policy,
            trajectory_policy=trajectory_policy,
            authorization_id=binding.verified.authorization_id,
            authority_artifact=binding.authority_artifact,
        )
        stable_mag1_event_id = mag1_evidence_event_id(
            trajectory_id=decision.updated_trajectory.trajectory_id,
            action_id=canonical_action.action_id,
        )

        if decision.disposition != Mag1Disposition.AUTO_ELIGIBLE:
            evidence_patch, queued_id = queue_mag1_evidence_patch(
                registry,
                decision=decision,
                trajectory_action=canonical_action,
                autonomy_policy=autonomy_policy,
                trajectory_policy=trajectory_policy,
                authorization_id=binding.verified.authorization_id,
                authority_artifact=binding.authority_artifact,
            )
            result = PrimeMag1TransitionResult(
                disposition=PrimeMag1TransitionDisposition.NOT_APPLIED,
                prime_id=record.prime_id,
                authorization_id=binding.verified.authorization_id,
                target_environment=binding.verified.target_environment.value,
                mag1_decision=decision,
                before_custody_sha256=before_hash,
                mag1_event_id=queued_id,
                release_reasons=[
                    "MAG-1 did not authorize automatic transition; protected state was not changed"
                ],
            )
            return evidence_patch, result

        containment = evaluate_overwatch_containment(
            registry,
            prime_id=binding.verified.prime_id,
            action=PRIME_MAG1_ACTION,
            target_environment=binding.verified.target_environment,
            verifier=overwatch_verifier,
            now=current_time,
        )

        if containment.active:
            working = dict(registry)
            mag1_patch, mag1_event_id = queue_mag1_evidence_patch(
                working,
                decision=decision,
                trajectory_action=canonical_action,
                autonomy_policy=autonomy_policy,
                trajectory_policy=trajectory_policy,
                authorization_id=binding.verified.authorization_id,
                authority_artifact=binding.authority_artifact,
            )
            if mag1_event_id != stable_mag1_event_id:
                raise PrimeMag1TransitionError("MAG-1 evidence event identity is unstable")
            working.update(mag1_patch)

            containment_event_id = _containment_event_id(
                containment=containment,
                authorization_id=binding.verified.authorization_id,
                trajectory_id=decision.updated_trajectory.trajectory_id,
                action_id=canonical_action.action_id,
            )
            containment_payload = {
                "schema": OVERWATCH_CONTAINMENT_BLOCK_SCHEMA,
                "prime_id": binding.verified.prime_id,
                "authorization_id": binding.verified.authorization_id,
                "target_environment": binding.verified.target_environment.value,
                "trajectory_id": decision.updated_trajectory.trajectory_id,
                "action_id": canonical_action.action_id,
                "directive_id": containment.directive_id,
                "directive_sha256": containment.directive_sha256,
                "sequence": containment.sequence,
                "reason_code": containment.reason_code,
                "signer_key_ids_sha256": _sha256(containment.signer_key_ids),
                "containment_snapshot_sha256": containment.snapshot_sha256,
                "before_custody_sha256": before_hash,
            }
            containment_patch, queued_containment_id = queue_event_outbox_patch(
                working,
                event=OVERWATCH_CONTAINMENT_BLOCK_EVENT,
                actor=OVERWATCH_CONTAINMENT_BLOCK_ACTOR,
                payload=containment_payload,
                event_id=containment_event_id,
            )
            if queued_containment_id != containment_event_id:
                raise PrimeMag1TransitionError(
                    "OVERWATCH containment event identity is unstable"
                )

            result = PrimeMag1TransitionResult(
                disposition=PrimeMag1TransitionDisposition.CONTAINED,
                prime_id=record.prime_id,
                authorization_id=binding.verified.authorization_id,
                target_environment=binding.verified.target_environment.value,
                mag1_decision=decision,
                before_custody_sha256=before_hash,
                mag1_event_id=mag1_event_id,
                overwatch_containment_event_id=containment_event_id,
                overwatch_directive_id=containment.directive_id,
                overwatch_directive_sha256=containment.directive_sha256,
                overwatch_sequence=containment.sequence,
                release_reasons=[
                    "OVERWATCH containment vetoed the transition before authority consumption or custody release"
                ],
            )
            return containment_patch, result

        if registry_witness_precondition is None:
            raise PrimeMag1TransitionError(
                "signed remote registry witness precondition is mandatory before PRIME release"
            )
        if registry_witness_verifier is None:
            raise PrimeMag1TransitionError(
                "pinned registry witness verifier is mandatory before PRIME release"
            )
        assert_registry_witness_precondition(
            registry,
            registry_witness_precondition,
            verifier=registry_witness_verifier,
        )
        witness_precondition_hash = _sha256(
            registry_witness_precondition.evidence()
        )

        bound_record = _bind_release_authorization(record, binding)
        released, activation_disposition, release_reasons = release_from_quarantine(
            bound_record,
            pack,
        )
        if activation_disposition != PrimeActivationDisposition.ACTIVATION_ALLOWED:
            raise PrimeMag1TransitionError(
                "custody release gate did not allow activation: "
                + "; ".join(release_reasons)
            )
        if released.state != PrimeCustodyState.READY:
            raise PrimeMag1TransitionError(
                "custody release did not transition PRIME to READY"
            )

        after_hash = custody_record_sha256(released)
        policy_hash = policy_bundle_sha256(autonomy_policy, trajectory_policy)
        transition_id = _transition_id(
            binding=binding,
            before_custody_sha256=before_hash,
            pack=pack,
            trajectory_id=decision.updated_trajectory.trajectory_id,
            action_id=canonical_action.action_id,
            policy_bundle_hash=policy_hash,
            overwatch_snapshot_sha256=containment.snapshot_sha256,
            registry_witness_precondition_sha256=witness_precondition_hash,
        )

        working = dict(registry)
        authorization_patch = consumed_authorization_registry_patch(
            working,
            authorization_id=binding.verified.authorization_id,
            transition_id=transition_id,
            consumed_at=current_time,
        )
        working.update(authorization_patch)

        custody_patch = prime_custody_registry_patch(working, released)
        working.update(custody_patch)

        mag1_patch, mag1_event_id = queue_mag1_evidence_patch(
            working,
            decision=decision,
            trajectory_action=canonical_action,
            autonomy_policy=autonomy_policy,
            trajectory_policy=trajectory_policy,
            authorization_id=binding.verified.authorization_id,
            authority_artifact=binding.authority_artifact,
        )
        if mag1_event_id != stable_mag1_event_id:
            raise PrimeMag1TransitionError("MAG-1 evidence event identity is unstable")
        working.update(mag1_patch)

        transition_event_id = _transition_event_id(transition_id)
        transition_payload = {
            "schema": PRIME_MAG1_TRANSITION_SCHEMA,
            "transition_id": transition_id,
            "prime_id": binding.verified.prime_id,
            "authorization_id": binding.verified.authorization_id,
            "target_environment": binding.verified.target_environment.value,
            "pack_id": pack.pack_id,
            "before_custody_sha256": before_hash,
            "after_custody_sha256": after_hash,
            "policy_bundle_sha256": policy_hash,
            "trajectory_id": decision.updated_trajectory.trajectory_id,
            "action_id": canonical_action.action_id,
            "mag1_event_id": mag1_event_id,
            "mag1_evidence_sha256": _sha256(mag1_payload),
            "release_reasons_sha256": _sha256(release_reasons),
            "overwatch_containment_snapshot_sha256": containment.snapshot_sha256,
            "overwatch_state": containment.state.value if containment.state else "NO_DIRECTIVE",
            "overwatch_sequence": containment.sequence,
            "overwatch_directive_id": containment.directive_id,
            "overwatch_directive_sha256": containment.directive_sha256,
            "registry_witness_required": True,
            "registry_witness_precondition_sha256": witness_precondition_hash,
            "registry_witness_receipt_sha256": registry_witness_precondition.witness_receipt_sha256,
            "registry_witness_id": registry_witness_precondition.witness_id,
            "registry_witness_mode": registry_witness_precondition.witness_mode,
            "registry_witness_independence_verified": False,
            "registry_witness_post_transition_covered": False,
        }
        transition_patch, queued_transition_id = queue_event_outbox_patch(
            working,
            event=PRIME_MAG1_TRANSITION_EVENT,
            actor=PRIME_MAG1_TRANSITION_ACTOR,
            payload=transition_payload,
            event_id=transition_event_id,
        )
        if queued_transition_id != transition_event_id:
            raise PrimeMag1TransitionError("transition event identity is unstable")
        working.update(transition_patch)

        patch: dict[str, Any] = {}
        patch.update(authorization_patch)
        patch.update(custody_patch)
        patch.update(transition_patch)

        result = PrimeMag1TransitionResult(
            disposition=PrimeMag1TransitionDisposition.APPLIED,
            transition_id=transition_id,
            prime_id=record.prime_id,
            authorization_id=binding.verified.authorization_id,
            target_environment=binding.verified.target_environment.value,
            mag1_decision=decision,
            before_custody_sha256=before_hash,
            after_custody_sha256=after_hash,
            mag1_event_id=mag1_event_id,
            transition_event_id=transition_event_id,
            overwatch_directive_id=containment.directive_id,
            overwatch_directive_sha256=containment.directive_sha256,
            overwatch_sequence=containment.sequence,
            registry_witness_receipt_sha256=registry_witness_precondition.witness_receipt_sha256,
            registry_witness_precondition_sha256=witness_precondition_hash,
            release_reasons=list(release_reasons),
        )
        return patch, result

    return store.transact_registry(operation)
