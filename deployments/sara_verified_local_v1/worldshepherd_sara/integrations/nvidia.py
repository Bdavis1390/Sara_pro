from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Final


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
        "architecture_version": "0.1",
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
