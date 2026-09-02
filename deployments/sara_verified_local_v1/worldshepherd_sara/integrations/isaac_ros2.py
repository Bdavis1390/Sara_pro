from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field

from .evidence import EvidenceEnvelope
from .nvidia import ClaimStatus, build_evidence_envelope


class IsaacRos2Observation(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    integration_id: Literal["WS-NV-01"] = "WS-NV-01"
    correlation_id: str = Field(min_length=8, max_length=128)
    bridge_version: str = Field(min_length=1, max_length=128)
    ros_distro: str = Field(min_length=1, max_length=64)
    simulation_state: Literal["playing", "paused", "stopped"]
    observed_topics: tuple[str, ...] = ()
    observed_services: tuple[str, ...] = ()


@dataclass(frozen=True)
class IsaacRos2InterfaceProof:
    observation: IsaacRos2Observation
    evidence: EvidenceEnvelope
    bridge_activity_observed: bool
    runtime_validated: bool = False
    claim_status: ClaimStatus = ClaimStatus.REQUIRES_LAB_VALIDATION

    def to_dict(self) -> dict[str, object]:
        return {
            "observation": self.observation.model_dump(mode="json"),
            "evidence": self.evidence.to_dict(),
            "bridge_activity_observed": self.bridge_activity_observed,
            "runtime_validated": self.runtime_validated,
            "claim_status": self.claim_status,
        }


def isaac_ros2_interface_contract() -> dict[str, object]:
    return {
        "increment": "WS-NV-01D",
        "surface": "isaac_sim_ros2",
        "transport_boundary": "ros2_topics_and_services",
        "simulation_playback_required_for_bridge_activity": True,
        "ros_client_implemented": False,
        "isaac_runtime_implemented": False,
        "network_calls_enabled": False,
        "runtime_validated": False,
        "claim_status": ClaimStatus.REQUIRES_LAB_VALIDATION,
    }


def assess_ros2_observation(
    *,
    observation: Mapping[str, Any],
    expected_correlation_id: str,
    configuration: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
    operator_authorization_ref: str | None = None,
) -> IsaacRos2InterfaceProof:
    """Parse captured Isaac/ROS 2 metadata without performing ROS communication."""

    parsed = IsaacRos2Observation.model_validate(observation)
    if parsed.correlation_id != expected_correlation_id:
        raise ValueError("Isaac ROS 2 correlation_id mismatch")

    activity = (
        parsed.simulation_state == "playing"
        and bool(parsed.observed_topics or parsed.observed_services)
    )
    envelope = build_evidence_envelope(
        surface_name="isaac_sim_ros2",
        config=configuration,
        evidence_refs=evidence_refs,
        operator_authorization_ref=operator_authorization_ref,
    )
    return IsaacRos2InterfaceProof(
        observation=parsed,
        evidence=envelope,
        bridge_activity_observed=activity,
    )
