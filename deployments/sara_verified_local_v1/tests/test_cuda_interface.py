from __future__ import annotations

from worldshepherd_sara.integrations.cuda_backend import (
    assess_cuda_observation,
    cuda_interface_contract,
)
from worldshepherd_sara.integrations.nvidia import ClaimStatus


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def test_cuda_contract_preserves_lab_validation_gate():
    contract = cuda_interface_contract()

    assert contract["increment"] == "WS-NV-01F"
    assert contract["version_inventory_required"] is True
    assert contract["compute_capability_required"] is True
    assert contract["workload_and_result_digests_required"] is True
    assert contract["cuda_client_implemented"] is False
    assert contract["gpu_discovery_implemented"] is False
    assert contract["runtime_validated"] is False
    assert contract["claim_status"] == ClaimStatus.REQUIRES_LAB_VALIDATION


def test_captured_cuda_success_does_not_validate_runtime():
    proof = assess_cuda_observation(
        observation={
            "schema_version": "1.0",
            "integration_id": "WS-NV-01",
            "correlation_id": "cuda-00000001",
            "driver_version": "unverified-example",
            "toolkit_version": "unverified-example",
            "device_name": "unverified-example",
            "compute_capability": "0.0",
            "workload_id": "fixture-workload",
            "workload_digest": SHA_A,
            "result_digest": SHA_B,
            "execution_status": "success",
        },
        expected_correlation_id="cuda-00000001",
        configuration={"source": "fixture", "network": False},
    )

    assert proof.execution_observed is True
    assert proof.runtime_validated is False
    assert proof.claim_status == ClaimStatus.REQUIRES_LAB_VALIDATION
    assert proof.evidence.claim_status == ClaimStatus.REQUIRES_LAB_VALIDATION.value


def test_cuda_not_run_is_not_execution_evidence():
    proof = assess_cuda_observation(
        observation={
            "schema_version": "1.0",
            "integration_id": "WS-NV-01",
            "correlation_id": "cuda-00000002",
            "driver_version": "unverified-example",
            "toolkit_version": "unverified-example",
            "device_name": "unverified-example",
            "compute_capability": "0.0",
            "workload_id": "fixture-workload",
            "workload_digest": SHA_A,
            "result_digest": None,
            "execution_status": "not_run",
        },
        expected_correlation_id="cuda-00000002",
        configuration={"source": "fixture", "network": False},
    )

    assert proof.execution_observed is False
    assert proof.runtime_validated is False
