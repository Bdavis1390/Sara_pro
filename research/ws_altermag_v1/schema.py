from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PhysicalState:
    material_id: str
    model_revision: str
    orientation_hkl: str
    thickness_nm: float | None
    temperature_K: float
    strain_tensor: tuple[float, ...] = field(default_factory=tuple)
    interface_stack: tuple[str, ...] = field(default_factory=tuple)
    execution_mode: str = "synthetic"

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Measurement:
    ef: float
    theta_rad: float
    phi_rad: float
    value: float
    sigma: float

    def as_record(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class InferenceResult:
    amplitude: float
    tau: float
    covariance: tuple[tuple[float, float], tuple[float, float]]
    condition_number: float
    identifiable: bool
    sse: float

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceDecision:
    allowed_claims: tuple[str, ...]
    blocked_promotions: tuple[str, ...]
    next_gate: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)
