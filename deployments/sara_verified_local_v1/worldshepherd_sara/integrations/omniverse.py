from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field

from .evidence import EvidenceEnvelope
from .nvidia import ClaimStatus, build_evidence_envelope


OMNIVERSE_PROOF_SCHEMA_VERSION = "1.0"


class OmniverseProbeRequest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    integration_id: Literal["WS-NV-01"] = "WS-NV-01"
    correlation_id: str = Field(min_length=8, max_length=128)
    operation: Literal["interface_probe"] = "interface_probe"
    requested_capabilities: tuple[str, ...] = (
        "kit_runtime",
        "services_core",
    )


class OmniverseProbeResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    integration_id: Literal["WS-NV-01"] = "WS-NV-01"
    correlation_id: str = Field(min_length=8, max_length=128)
    service_id: str = Field(min_length=1, max_length=128)
    kit_version: str = Field(min_length=1, max_length=128)
    service_status: Literal["ready", "degraded", "unavailable"]
    extension_versions: dict[str, str] = Field(default_factory=dict)
    observed_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class OmniverseInterfaceProof:
    response: OmniverseProbeResponse
    evidence: EvidenceEnvelope
    interface_parsed: bool = True
    runtime_validated: bool = False
    claim_status: ClaimStatus = ClaimStatus.REQUIRES_PARTNER_VALIDATION

    def to_dict(self) -> dict[str, object]:
        return {
            "response": self.response.model_dump(mode="json"),
            "evidence": self.evidence.to_dict(),
            "interface_parsed": self.interface_parsed,
            "runtime_validated": self.runtime_validated,
            "claim_status": self.claim_status,
        }


def omniverse_interface_contract() -> dict[str, object]:
    """Describe the WS-NV-01C wire contract without executing it."""

    return {
        "increment": "WS-NV-01C",
        "surface": "omniverse_kit",
        "proof_schema_version": OMNIVERSE_PROOF_SCHEMA_VERSION,
        "transport_boundary": "http_openapi_compatible_service",
        "intended_runtime": "headless_omniverse_kit_service",
        "sara_network_client_implemented": False,
        "omniverse_service_implemented": False,
        "network_calls_enabled": False,
        "runtime_validated": False,
        "claim_status": ClaimStatus.REQUIRES_PARTNER_VALIDATION,
    }


def build_probe_request(*, correlation_id: str) -> OmniverseProbeRequest:
    """Build the request payload a future Omniverse service must accept."""

    return OmniverseProbeRequest(correlation_id=correlation_id)


def assess_probe_response(
    *,
    response: Mapping[str, Any],
    expected_correlation_id: str,
    configuration: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
    operator_authorization_ref: str | None = None,
) -> OmniverseInterfaceProof:
    """Parse a captured service response and wrap it in evidence without promotion.

    This function performs no network I/O. A syntactically valid response proves
    only that the captured payload conforms to the WS-NV-01C interface contract.
    It does not prove that Omniverse Kit produced the response or that a runtime is
    operational; provenance for that must be established separately.
    """

    parsed = OmniverseProbeResponse.model_validate(response)
    if parsed.correlation_id != expected_correlation_id:
        raise ValueError("Omniverse probe correlation_id mismatch")

    envelope = build_evidence_envelope(
        surface_name="omniverse_kit",
        config=configuration,
        evidence_refs=evidence_refs,
        operator_authorization_ref=operator_authorization_ref,
    )
    return OmniverseInterfaceProof(response=parsed, evidence=envelope)
