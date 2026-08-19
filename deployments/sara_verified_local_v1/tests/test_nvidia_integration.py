from __future__ import annotations

import pytest

from worldshepherd_sara.integrations.evidence import canonical_config_digest
from worldshepherd_sara.integrations.nvidia import (
    ClaimStatus,
    IntegrationState,
    SURFACES,
    build_evidence_envelope,
    integration_manifest,
    integration_status,
)


def test_ws_nv_01_is_non_executing_by_default():
    manifest = integration_manifest()

    assert manifest["integration_id"] == "WS-NV-01"
    assert manifest["vendor"] == "NVIDIA"
    assert manifest["execution_mode"] == "contract_and_offline_evidence_only"
    assert manifest["network_calls_enabled"] is False
    assert manifest["runtime_verified"] is False
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


def test_manifest_reports_all_current_proof_contract_increments():
    manifest = integration_manifest()

    assert manifest["implemented_increments"] == [
        "WS-NV-01",
        "WS-NV-01A",
        "WS-NV-01B",
        "WS-NV-01C",
        "WS-NV-01D",
        "WS-NV-01E",
        "WS-NV-01F",
        "WS-NV-01G",
    ]
    assert manifest["promotion_gate"] == {
        "required_categories": [
            "runtime_version_inventory",
            "configuration_digest",
            "bounded_interface_test",
            "telemetry_and_provenance",
            "failure_or_degraded_behavior",
            "operator_authorization",
        ],
        "auto_promotion_allowed": False,
        "human_review_required": True,
    }
    assert set(manifest["proof_contracts"]) == {
        "omniverse_kit",
        "isaac_sim_ros2",
        "jetson_platform_services",
        "cuda_acceleration",
    }


def test_status_exposes_digest_without_promoting_runtime():
    status = integration_status()

    assert status["status"] == "proof_contracts_ready_runtime_unverified"
    assert status["runtime_verified"] is False
    assert status["network_calls_enabled"] is False
    assert status["surface_count"] == 4
    assert str(status["contract_digest"]).startswith("sha256:")
    assert len(str(status["contract_digest"])) == len("sha256:") + 64
    assert all(item["state"] != IntegrationState.VALIDATED for item in status["surfaces"])


def test_configuration_digest_is_canonical_and_deterministic():
    left = canonical_config_digest({"b": 2, "a": {"z": 3, "y": 4}})
    right = canonical_config_digest({"a": {"y": 4, "z": 3}, "b": 2})

    assert left == right
    assert left.startswith("sha256:")


def test_evidence_envelope_records_digest_not_raw_config_and_preserves_claim():
    config = {"sdk": "unverified", "mode": "simulation", "network": False}
    envelope = build_evidence_envelope(
        surface_name="isaac_sim_ros2",
        config=config,
        evidence_refs=["test://bounded-interface-001"],
        operator_authorization_ref="auth://CRE1AWS/example",
    )
    body = envelope.to_dict()

    assert body["integration_id"] == "WS-NV-01"
    assert body["surface"] == "isaac_sim_ros2"
    assert body["claim_status"] == ClaimStatus.REQUIRES_LAB_VALIDATION.value
    assert body["config_digest"] == canonical_config_digest(config)
    assert "config" not in body
    assert body["evidence_refs"] == ("test://bounded-interface-001",)
    assert body["operator_authorization_ref"] == "auth://CRE1AWS/example"


def test_unknown_surface_cannot_receive_nvidia_evidence_envelope():
    with pytest.raises(ValueError, match="Unknown NVIDIA integration surface"):
        build_evidence_envelope(surface_name="invented_runtime", config={})
