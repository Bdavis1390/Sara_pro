from __future__ import annotations

from worldshepherd_sara.integrations.isaac_ros2 import (
    assess_ros2_observation,
    isaac_ros2_interface_contract,
)
from worldshepherd_sara.integrations.jetson import (
    assess_jetson_observation,
    jetson_interface_contract,
)
from worldshepherd_sara.integrations.nvidia import ClaimStatus


def test_isaac_ros2_contract_preserves_lab_validation_gate():
    contract = isaac_ros2_interface_contract()

    assert contract["increment"] == "WS-NV-01D"
    assert contract["simulation_playback_required_for_bridge_activity"] is True
    assert contract["network_calls_enabled"] is False
    assert contract["runtime_validated"] is False
    assert contract["claim_status"] == ClaimStatus.REQUIRES_LAB_VALIDATION


def test_isaac_activity_requires_playback_and_observed_ros_surface():
    active = assess_ros2_observation(
        observation={
            "schema_version": "1.0",
            "integration_id": "WS-NV-01",
            "correlation_id": "isaac-00000001",
            "bridge_version": "unverified-example",
            "ros_distro": "unverified-example",
            "simulation_state": "playing",
            "observed_topics": ["/clock"],
            "observed_services": [],
        },
        expected_correlation_id="isaac-00000001",
        configuration={"source": "fixture", "network": False},
    )
    paused = assess_ros2_observation(
        observation={
            "schema_version": "1.0",
            "integration_id": "WS-NV-01",
            "correlation_id": "isaac-00000002",
            "bridge_version": "unverified-example",
            "ros_distro": "unverified-example",
            "simulation_state": "paused",
            "observed_topics": ["/clock"],
            "observed_services": [],
        },
        expected_correlation_id="isaac-00000002",
        configuration={"source": "fixture", "network": False},
    )

    assert active.bridge_activity_observed is True
    assert paused.bridge_activity_observed is False
    assert active.runtime_validated is False
    assert active.evidence.claim_status == ClaimStatus.REQUIRES_LAB_VALIDATION.value


def test_jetson_contract_preserves_lab_validation_gate():
    contract = jetson_interface_contract()

    assert contract["increment"] == "WS-NV-01E"
    assert contract["transport_boundary"] == "rest_api_service"
    assert contract["network_calls_enabled"] is False
    assert contract["runtime_validated"] is False
    assert contract["claim_status"] == ClaimStatus.REQUIRES_LAB_VALIDATION


def test_jetson_captured_api_surface_does_not_validate_runtime():
    proof = assess_jetson_observation(
        observation={
            "schema_version": "1.0",
            "integration_id": "WS-NV-01",
            "correlation_id": "jetson-00000001",
            "service_id": "fixture-service",
            "service_kind": "ai_service_fixture",
            "jetpack_version": "unverified-example",
            "platform_services_version": "unverified-example",
            "service_status": "ready",
            "observed_api_operations": ["fixture://status"],
            "containerized": True,
        },
        expected_correlation_id="jetson-00000001",
        configuration={"source": "fixture", "network": False},
    )

    assert proof.api_surface_observed is True
    assert proof.runtime_validated is False
    assert proof.claim_status == ClaimStatus.REQUIRES_LAB_VALIDATION
    assert proof.evidence.claim_status == ClaimStatus.REQUIRES_LAB_VALIDATION.value
