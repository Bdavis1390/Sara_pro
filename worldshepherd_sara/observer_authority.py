"""Authority completeness checks for external fusion-state observers.

This module does not decide whether a scientific source is actually authoritative.
It verifies that an external observer packet explicitly carries the categories of
machine/reconstruction authority needed for independent review before the observer
can be promoted beyond an analysis-only integration candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple


REQUIRED_AUTHORITY_FIELDS = (
    "diagnostic_geometry_and_calibration",
    "passive_structure_model",
    "response_matrices_or_generation_method",
    "reconstruction_settings",
    "coordinate_conventions",
)

OPTIONAL_AUTHORITY_FIELDS = (
    "profile_or_kinetic_constraints",
)


@dataclass(frozen=True)
class ObserverAuthorityPacket:
    device: str
    reconstruction_family: str
    authority_provenance: Mapping[str, str]
    validated_by: str
    validation_reference: str

    def validate(self) -> Tuple[bool, str]:
        if not self.device.strip():
            return False, "device_missing"
        if not self.reconstruction_family.strip():
            return False, "reconstruction_family_missing"
        if not self.validated_by.strip():
            return False, "validated_by_missing"
        if not self.validation_reference.strip():
            return False, "validation_reference_missing"

        for field in REQUIRED_AUTHORITY_FIELDS:
            value = self.authority_provenance.get(field, "")
            if not isinstance(value, str) or not value.strip():
                return False, f"authority_missing:{field}"

        return True, "ok"

    @property
    def authority_complete(self) -> bool:
        ok, _ = self.validate()
        return ok


def missing_authorities(packet: ObserverAuthorityPacket) -> Tuple[str, ...]:
    missing = []
    for field in REQUIRED_AUTHORITY_FIELDS:
        value = packet.authority_provenance.get(field, "")
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return tuple(missing)
