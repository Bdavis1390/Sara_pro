"""Vendor integration contracts for Worldshepherd SARA.

Integration modules in this package define bounded interfaces and evidence gates.
They do not imply that an external vendor runtime is installed, connected, or
validated unless the module explicitly reports that state.
"""

from .cuda_backend import assess_cuda_observation, cuda_interface_contract
from .isaac_ros2 import assess_ros2_observation, isaac_ros2_interface_contract
from .jetson import assess_jetson_observation, jetson_interface_contract
from .nvidia import build_evidence_envelope, integration_manifest, integration_status
from .omniverse import (
    assess_probe_response,
    build_probe_request,
    omniverse_interface_contract,
)

__all__ = [
    "assess_cuda_observation",
    "assess_jetson_observation",
    "assess_probe_response",
    "assess_ros2_observation",
    "build_evidence_envelope",
    "build_probe_request",
    "cuda_interface_contract",
    "integration_manifest",
    "integration_status",
    "isaac_ros2_interface_contract",
    "jetson_interface_contract",
    "omniverse_interface_contract",
]
