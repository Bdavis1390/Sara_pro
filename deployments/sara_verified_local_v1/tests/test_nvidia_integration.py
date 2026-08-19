from __future__ import annotations

from worldshepherd_sara.integrations.nvidia import (
    ClaimStatus,
    IntegrationState,
    SURFACES,
    integration_manifest,
)


def test_ws_nv_01_is_non_executing_by_default():
    manifest = integration_manifest()

    assert manifest["integration_id"] == "WS-NV-01"
    assert manifest["vendor"] == "NVIDIA"
    assert manifest["execution_mode"] == "scaffold_only"
    assert manifest["network_calls_enabled"] is False
    assert manifest["contract_claim"] == ClaimStatus.IMPLEMENTED_IN_SOFTWARE
    assert manifest["vendor_capability_claim"] == ClaimStatus.REQUIRES_PARTNER_VALIDATION


def test_no_nvidia_surface_is_silently_promoted_to_validated():
    assert SURFACES
    assert all(surface.state != IntegrationState.VALIDATED for surface in SURFACES)
    assert all(surface.network_calls_enabled is False for surface in SURFACES)


def test_required_nvidia_surfaces_are_declared():
    names = {surface.name for surface in SURFACES}

    assert names == {
        "omniverse_kit",
        "isaac_sim_ros2",
        "jetson_platform_services",
        "cuda_acceleration",
    }


def test_evidence_gate_covers_runtime_provenance_and_failure_behavior():
    required = set(integration_manifest()["evidence_required"])

    assert "runtime and SDK version inventory" in required
    assert "reproducible configuration digest" in required
    assert "telemetry and decision-provenance capture" in required
    assert "failure and degraded-state behavior" in required
    assert "operator authorization record" in required
