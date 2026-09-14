#!/usr/bin/env python3
"""Registry adapter for the WS-QPHONON L2 governed parameter state.

This module normalizes evidence into a stable registry record. It performs no
quantum inference and makes no physical-capability claim. Missing decision-
critical parameters remain missing rather than being synthesized.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


REQUIRED_PARAMETER_KEYS = (
    "g1_hz",
    "g2_hz",
    "kappa_m_hz",
    "gamma_eff_hz",
    "t2_s",
    "t1_s",
    "detuning_hz",
    "device_temperature_k",
    "thermal_occupation",
    "acoustic_drive_hz",
    "orbital_leakage_probability",
    "transducer_response",
)


@dataclass(frozen=True)
class RegistryRecord:
    schema: str
    integration_level: str
    claims_state: str
    parameters: dict[str, Any]
    provenance: dict[str, Any]
    complete: bool
    missing_parameters: list[str]


def build_record(
    config: dict[str, Any],
    parameters: dict[str, Any],
    provenance: dict[str, Any],
) -> RegistryRecord:
    """Build a normalized registry record without inventing absent values."""
    configured = config.get("parameter_registry", {})
    missing = [
        key for key in REQUIRED_PARAMETER_KEYS
        if key not in parameters or parameters[key] is None
    ]

    unknown = sorted(set(parameters) - set(configured))
    if unknown:
        raise ValueError(f"unregistered QPHONON parameters: {unknown}")

    normalized = {key: parameters[key] for key in REQUIRED_PARAMETER_KEYS if key in parameters}
    return RegistryRecord(
        schema="WS-QPHONON-REGISTRY-RECORD-V0.1",
        integration_level=str(config.get("integration_level", "UNKNOWN")),
        claims_state=str(config.get("status", "UNKNOWN")),
        parameters=normalized,
        provenance=dict(provenance),
        complete=not missing,
        missing_parameters=missing,
    )


def to_dict(record: RegistryRecord) -> dict[str, Any]:
    return asdict(record)
