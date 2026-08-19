from __future__ import annotations

import pytest

from worldshepherd_sara.integrations.nvidia import ClaimStatus
from worldshepherd_sara.integrations.omniverse import (
    assess_probe_response,
    build_probe_request,
    omniverse_interface_contract,
)


def test_omniverse_interface_contract_is_non_executing_and_unvalidated():
    contract = omniverse_interface_contract()

    assert contract["increment"] == "WS-NV-01C"
    assert contract["surface"] == "omniverse_kit"
    assert contract["network_calls_enabled"] is False
    assert contract["sara_network_client_implemented"] is False
    assert contract["omniverse_service_implemented"] is False
    assert contract["runtime_validated"] is False
    assert contract["claim_status"] == ClaimStatus.REQUIRES_PARTNER_VALIDATION


def test_probe_request_defines_expected_wire_payload():
    request = build_probe_request(correlation_id="corr-00000001")
    body = request.model_dump(mode="json")

    assert body == {
        "schema_version": "1.0",
        "integration_id": "WS-NV-01",
        "correlation_id": "corr-00000001",
        "operation": "interface_probe",
        "requested_capabilities": ["kit_runtime", "services_core"],
    }


def test_captured_probe_response_can_be_parsed_without_runtime_promotion():
    proof = assess_probe_response(
        response={
            "schema_version": "1.0",
            "integration_id": "WS-NV-01",
            "correlation_id": "corr-00000002",
            "service_id": "partner-captured-example",
            "kit_version": "unverified-example",
            "service_status": "ready",
            "extension_versions": {"omni.services.core": "unverified-example"},
            "observed_capabilities": ["kit_runtime", "services_core"],
        },
        expected_correlation_id="corr-00000002",
        configuration={"source": "captured-fixture", "network": False},
        evidence_refs=["test://omniverse-interface-fixture"],
    )
    body = proof.to_dict()

    assert body["interface_parsed"] is True
    assert body["runtime_validated"] is False
    assert body["claim_status"] == ClaimStatus.REQUIRES_PARTNER_VALIDATION
    assert body["evidence"]["claim_status"] == (
        ClaimStatus.REQUIRES_PARTNER_VALIDATION.value
    )
    assert "configuration" not in body["evidence"]


def test_probe_response_correlation_mismatch_is_rejected():
    with pytest.raises(ValueError, match="correlation_id mismatch"):
        assess_probe_response(
            response={
                "schema_version": "1.0",
                "integration_id": "WS-NV-01",
                "correlation_id": "corr-00000003",
                "service_id": "fixture",
                "kit_version": "unverified-example",
                "service_status": "degraded",
            },
            expected_correlation_id="corr-00000004",
            configuration={},
        )
