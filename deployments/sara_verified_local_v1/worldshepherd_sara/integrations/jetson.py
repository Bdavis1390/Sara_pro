from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field

from .evidence import EvidenceEnvelope
from .nvidia import ClaimStatus, build_evidence_envelope


class JetsonServiceObservation(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    integration_id: Literal["WS-NV-01"] = "WS-NV-01"
    correlation_id: str = Field(min_length=8, max_length=128)
    service_id: str = Field(min_length=1, max_length=128)
    service_kind: str = Field(min_length=1, max_length=128)
    jetpack_version: str = Field(min_length=1, max_length=128)
    platform_services_version: str = Field(min_length=1, max_length=128)
    service_status: Literal["ready", "degraded", "unavailable"]
    observed_api_operations: tuple[str, ...] = ()
    containerized: bool


@dataclass(frozen=True)
class JetsonInterfaceProof:
    observation: JetsonServiceObservation
    evidence: EvidenceEnvelope
    api_surface_observed: bool
    runtime_validated: bool = False
    claim_status: ClaimStatus = ClaimStatus.REQUIRES_LAB_VALIDATION

    def to_dict(self) -> dict[str, object]:
        return {
            "observation": self.observation.model_dump(mode="json"),
            "evidence": self.evidence.to_dict(),
            "api_surface_observed": self.api_surface_observed,
            "runtime_validated": self.runtime_validated,
            "claim_status": self.claim_status,
        }


def jetson_interface_contract() -> dict[str, object]:
    return {
        "increment": "WS-NV-01E",
        "surface": "jetson_platform_services",
        "transport_boundary": "rest_api_service",
        "intended_deployment": "containerized_edge_service",
        "sara_network_client_implemented": False,
        "jetson_runtime_implemented": False,
        "network_calls_enabled": False,
        "runtime_validated": False,
        "claim_status": ClaimStatus.REQUIRES_LAB_VALIDATION,
    }


def assess_jetson_observation(
    *,
    observation: Mapping[str, Any],
    expected_correlation_id: str,
    configuration: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
    operator_authorization_ref: str | None = None,
) -> JetsonInterfaceProof:
    """Parse captured Jetson service metadata without performing REST calls."""

    parsed = JetsonServiceObservation.model_validate(observation)
    if parsed.correlation_id != expected_correlation_id:
        raise ValueError("Jetson service correlation_id mismatch")

    api_surface_observed = bool(parsed.observed_api_operations)
    envelope = build_evidence_envelope(
        surface_name="jetson_platform_services",
        config=configuration,
        evidence_refs=evidence_refs,
        operator_authorization_ref=operator_authorization_ref,
    )
    return JetsonInterfaceProof(
        observation=parsed,
        evidence=envelope,
        api_surface_observed=api_surface_observed,
    )
