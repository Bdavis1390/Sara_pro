"""Vendor integration contracts for Worldshepherd SARA.

Integration modules in this package define bounded interfaces and evidence gates.
They do not imply that an external vendor runtime is installed, connected, or
validated unless the module explicitly reports that state.
"""

from .nvidia import build_evidence_envelope, integration_manifest, integration_status
from .omniverse import (
    assess_probe_response,
    build_probe_request,
    omniverse_interface_contract,
)

__all__ = [
    "assess_probe_response",
    "build_evidence_envelope",
    "build_probe_request",
    "integration_manifest",
    "integration_status",
    "omniverse_interface_contract",
]
