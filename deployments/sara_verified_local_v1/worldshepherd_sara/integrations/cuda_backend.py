from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field

from .evidence import EvidenceEnvelope
from .nvidia import ClaimStatus, build_evidence_envelope


class CudaComputeObservation(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    integration_id: Literal["WS-NV-01"] = "WS-NV-01"
    correlation_id: str = Field(min_length=8, max_length=128)
    driver_version: str = Field(min_length=1, max_length=128)
    toolkit_version: str = Field(min_length=1, max_length=128)
    device_name: str = Field(min_length=1, max_length=256)
    compute_capability: str = Field(min_length=3, max_length=32)
    workload_id: str = Field(min_length=1, max_length=128)
    workload_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    result_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    execution_status: Literal["success", "failed", "not_run"]


@dataclass(frozen=True)
class CudaInterfaceProof:
    observation: CudaComputeObservation
    evidence: EvidenceEnvelope
    execution_observed: bool
    runtime_validated: bool = False
    claim_status: ClaimStatus = ClaimStatus.REQUIRES_LAB_VALIDATION

    def to_dict(self) -> dict[str, object]:
        return {
            "observation": self.observation.model_dump(mode="json"),
            "evidence": self.evidence.to_dict(),
            "execution_observed": self.execution_observed,
            "runtime_validated": self.runtime_validated,
            "claim_status": self.claim_status,
        }


def cuda_interface_contract() -> dict[str, object]:
    return {
        "increment": "WS-NV-01F",
        "surface": "cuda_acceleration",
        "transport_boundary": "future_compute_backend",
        "version_inventory_required": True,
        "compute_capability_required": True,
        "workload_and_result_digests_required": True,
        "cuda_client_implemented": False,
        "gpu_discovery_implemented": False,
        "runtime_validated": False,
        "claim_status": ClaimStatus.REQUIRES_LAB_VALIDATION,
    }


def assess_cuda_observation(
    *,
    observation: Mapping[str, Any],
    expected_correlation_id: str,
    configuration: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
    operator_authorization_ref: str | None = None,
) -> CudaInterfaceProof:
    """Parse captured CUDA execution metadata without importing or invoking CUDA."""

    parsed = CudaComputeObservation.model_validate(observation)
    if parsed.correlation_id != expected_correlation_id:
        raise ValueError("CUDA observation correlation_id mismatch")

    execution_observed = (
        parsed.execution_status == "success" and parsed.result_digest is not None
    )
    envelope = build_evidence_envelope(
        surface_name="cuda_acceleration",
        config=configuration,
        evidence_refs=evidence_refs,
        operator_authorization_ref=operator_authorization_ref,
    )
    return CudaInterfaceProof(
        observation=parsed,
        evidence=envelope,
        execution_observed=execution_observed,
    )
