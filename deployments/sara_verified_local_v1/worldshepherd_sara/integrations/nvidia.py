from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Final, Mapping, Sequence

from .evidence import (
    EVIDENCE_ENVELOPE_SCHEMA_VERSION,
    EvidenceEnvelope,
    canonical_config_digest,
)


class IntegrationState(StrEnum):
    CONTRACT_DEFINED = "contract_defined"
    RUNTIME_NOT_VERIFIED = "runtime_not_verified"
    VALIDATED = "validated"


class ClaimStatus(StrEnum):
    IMPLEMENTED_IN_SOFTWARE = "IMPLEMENTED_IN_SOFTWARE"
    REQUIRES_LAB_VALIDATION = "REQUIRES_LAB_VALIDATION"
    REQUIRES_PARTNER_VALIDATION = "REQUIRES_PARTNER_VALIDATION"


@dataclass(frozen=True)
class NvidiaSurfaceContract:
    name: str
    transport: str
    purpose: str
    state: IntegrationState
    capability_claim: ClaimStatus
    network_calls_enabled: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


SURFACES: Final[tuple[NvidiaSurfaceContract, ...]] = (
    NvidiaSurfaceContract(
        name="omniverse_kit",
        transport="headless_app_or_microservice_boundary",
        purpose="digital-twin and simulation event exchange",
        state=IntegrationState.RUNTIME_NOT_VERIFIED,
        capability_claim=ClaimStatus.REQUIRES_PARTNER_VALIDATION,
    ),
    NvidiaSurfaceContract(
        name="isaac_sim_ros2",
        transport="ros2_bridge_boundary",
        purpose="robotics simulation, synthetic data, and control-loop exchange",
        state=IntegrationState.RUNTIME_NOT_VERIFIED,
        capability_claim=ClaimStatus.REQUIRES_LAB_VALIDATION,
    ),
    NvidiaSurfaceContract(
        name="jetson_platform_services",
        transport="api_service_boundary",
        purpose="edge-AI service orchestration and telemetry exchange",
        state=IntegrationState.RUNTIME_NOT_VERIFIED,
        capability_claim=ClaimStatus.REQUIRES_LAB_VALIDATION,
    ),
    NvidiaSurfaceContract(
        name="cuda_acceleration",
        transport="future_compute_backend",
        purpose="optional accelerated compute for approved workloads",
        state=IntegrationState.RUNTIME_NOT_VERIFIED,
        capability_claim=ClaimStatus.REQUIRES_LAB_VALIDATION,
    ),
)


def integration_manifest() -> dict[str, object]:
    """Return the non-executing WS-NV-01 integration contract.

    This function deliberately performs no vendor imports, network calls, device
    discovery, or hardware claims. It describes the interfaces Worldshepherd
    intends to validate and the evidence gates that still remain.
    """

    return {
        "integration_id": "WS-NV-01",
        "vendor": "NVIDIA",
        "architecture_version": "0.2",
        "execution_mode": "scaffold_only",
        "network_calls_enabled": False,
        "contract_claim": ClaimStatus.IMPLEMENTED_IN_SOFTWARE,
        "vendor_capability_claim": ClaimStatus.REQUIRES_PARTNER_VALIDATION,
        "promotion_rule": (
            "No NVIDIA runtime capability may be promoted beyond its current "
            "claim state without reproducible lab or partner evidence."
        ),
        "evidence_required": [
            "runtime and SDK version inventory",
            "reproducible configuration digest",
            "successful bounded interface test",
            "telemetry and decision-provenance capture",
            "failure and degraded-state behavior",
            "operator authorization record",
        ],
        "surfaces": [surface.to_dict() for surface in SURFACES],
    }


def integration_status() -> dict[str, object]:
    """Return an authenticated-read-safe status snapshot for WS-NV-01."""

    manifest = integration_manifest()
    return {
        "integration_id": manifest["integration_id"],
        "vendor": manifest["vendor"],
        "architecture_version": manifest["architecture_version"],
        "status": "contract_ready_runtime_unverified",
        "execution_mode": manifest["execution_mode"],
        "network_calls_enabled": False,
        "runtime_verified": False,
        "surface_count": len(SURFACES),
        "contract_claim": manifest["contract_claim"],
        "vendor_capability_claim": manifest["vendor_capability_claim"],
        "contract_digest": canonical_config_digest(manifest),
        "evidence_envelope_schema_version": EVIDENCE_ENVELOPE_SCHEMA_VERSION,
        "surfaces": [
            {
                "name": surface.name,
                "state": surface.state,
                "capability_claim": surface.capability_claim,
                "network_calls_enabled": surface.network_calls_enabled,
            }
            for surface in SURFACES
        ],
    }


def build_evidence_envelope(
    *,
    surface_name: str,
    config: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
    operator_authorization_ref: str | None = None,
) -> EvidenceEnvelope:
    """Build a configuration-digested evidence envelope for one declared surface.

    Creating an envelope does not validate the runtime or promote the claim. The
    envelope inherits the surface's current claim status until separate evidence
    justifies an explicit promotion through a future controlled workflow.
    """

    try:
        surface = next(item for item in SURFACES if item.name == surface_name)
    except StopIteration as exc:
        raise ValueError(f"Unknown NVIDIA integration surface: {surface_name}") from exc

    return EvidenceEnvelope.create(
        integration_id="WS-NV-01",
        surface=surface.name,
        claim_status=surface.capability_claim.value,
        config=config,
        evidence_refs=evidence_refs,
        operator_authorization_ref=operator_authorization_ref,
    )
