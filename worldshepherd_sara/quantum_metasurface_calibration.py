"""Fail-closed full-wave calibration gate for the WS-METASURFACE quantum challenger.

The existing Worldshepherd metasurface control model defines fields, phase/material
actuation, Maxwell coupling and thermal/material state variables. Those equations are
not themselves a calibrated reduced-order objective. Before WS-METASURFACE may leave
synthetic-surrogate evidence, a reduced model must be compared against retained
full-wave EM data under the same geometry, materials, excitation and frequency grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from math import sqrt
from pathlib import Path
import re
from typing import Sequence


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLACEHOLDER = ("placeholder", "todo", "tbd", "unknown", "replace-me", "<", ">")


class FullWaveSolverClass(str, Enum):
    FEM = "fem"
    FDTD = "fdtd"
    MOM = "mom"
    FEM_BEM = "fem_bem"
    OTHER_VALIDATED_MAXWELL = "other_validated_maxwell"


@dataclass(frozen=True)
class FullWaveCalibrationRecord:
    project_id: str
    calibration_id: str
    solver_class: FullWaveSolverClass
    solver_name: str
    solver_version: str
    geometry_digest: str
    mesh_or_discretization_digest: str
    material_model_digest: str
    boundary_condition_digest: str
    excitation_digest: str
    frequency_grid_digest: str
    tile_state_map_digest: str
    full_wave_result_digest: str
    reduced_model_digest: str
    reduced_result_digest: str
    full_wave_artifact_digest: str
    reduced_artifact_digest: str
    sample_count: int
    phase_rmse_deg: float
    magnitude_rmse_db: float
    max_phase_error_deg: float
    max_magnitude_error_db: float
    pass_phase_rmse_deg: float
    pass_magnitude_rmse_db: float
    pass_max_phase_error_deg: float
    pass_max_magnitude_error_db: float
    source_reference: str
    environment: str = "simulation"
    claim_control: str = (
        "Calibration record only. Agreement with a full-wave solver establishes reduced-model fidelity only for the frozen geometry, "
        "materials, excitation, state map and frequency grid. It does not validate RF hardware or quantum advantage."
    )


@dataclass(frozen=True)
class FullWaveCalibrationDecision:
    accepted: bool
    reasons: tuple[str, ...]
    gate_id: str
    calibration_id: str
    claim_control: str


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def artifact_digest(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _is_sha(value: str) -> bool:
    return bool(_SHA256.fullmatch(value.strip().lower()))


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(token in lowered for token in _PLACEHOLDER)


def compare_complex_response(
    full_wave_phase_deg: Sequence[float],
    reduced_phase_deg: Sequence[float],
    full_wave_magnitude_db: Sequence[float],
    reduced_magnitude_db: Sequence[float],
) -> dict[str, float | int]:
    lengths = {len(full_wave_phase_deg), len(reduced_phase_deg), len(full_wave_magnitude_db), len(reduced_magnitude_db)}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) < 3:
        raise ValueError("full-wave/reduced phase and magnitude series must have equal length >= 3")

    def phase_delta(a: float, b: float) -> float:
        return ((float(a) - float(b) + 180.0) % 360.0) - 180.0

    phase_errors = [phase_delta(a, b) for a, b in zip(full_wave_phase_deg, reduced_phase_deg)]
    magnitude_errors = [float(a) - float(b) for a, b in zip(full_wave_magnitude_db, reduced_magnitude_db)]
    n = len(phase_errors)
    return {
        "sample_count": n,
        "phase_rmse_deg": sqrt(sum(error * error for error in phase_errors) / n),
        "magnitude_rmse_db": sqrt(sum(error * error for error in magnitude_errors) / n),
        "max_phase_error_deg": max(abs(error) for error in phase_errors),
        "max_magnitude_error_db": max(abs(error) for error in magnitude_errors),
    }


def validate_full_wave_calibration(
    record: FullWaveCalibrationRecord,
    *,
    full_wave_artifact: str | Path | None = None,
    reduced_artifact: str | Path | None = None,
) -> FullWaveCalibrationDecision:
    reasons: list[str] = []
    if record.project_id != "WS-METASURFACE":
        reasons.append("project_id must be WS-METASURFACE")
    for name in ("calibration_id", "solver_name", "solver_version", "source_reference"):
        if _is_placeholder(str(getattr(record, name))):
            reasons.append(f"{name} must be concrete and non-placeholder")
    for name in (
        "geometry_digest", "mesh_or_discretization_digest", "material_model_digest", "boundary_condition_digest",
        "excitation_digest", "frequency_grid_digest", "tile_state_map_digest", "full_wave_result_digest",
        "reduced_model_digest", "reduced_result_digest", "full_wave_artifact_digest", "reduced_artifact_digest",
    ):
        if not _is_sha(str(getattr(record, name))):
            reasons.append(f"{name} must be a sha256 digest")
    if record.sample_count < 3:
        reasons.append("sample_count must be >= 3")
    for name in (
        "phase_rmse_deg", "magnitude_rmse_db", "max_phase_error_deg", "max_magnitude_error_db",
        "pass_phase_rmse_deg", "pass_magnitude_rmse_db", "pass_max_phase_error_deg", "pass_max_magnitude_error_db",
    ):
        value = float(getattr(record, name))
        if value < 0 or value == float("inf"):
            reasons.append(f"{name} must be finite and non-negative")
    if record.pass_phase_rmse_deg <= 0 or record.pass_magnitude_rmse_db <= 0:
        reasons.append("RMSE acceptance thresholds must be positive")
    if record.pass_max_phase_error_deg <= 0 or record.pass_max_magnitude_error_db <= 0:
        reasons.append("maximum-error acceptance thresholds must be positive")
    if record.phase_rmse_deg > record.pass_phase_rmse_deg:
        reasons.append("phase RMSE exceeds frozen acceptance threshold")
    if record.magnitude_rmse_db > record.pass_magnitude_rmse_db:
        reasons.append("magnitude RMSE exceeds frozen acceptance threshold")
    if record.max_phase_error_deg > record.pass_max_phase_error_deg:
        reasons.append("maximum phase error exceeds frozen acceptance threshold")
    if record.max_magnitude_error_db > record.pass_max_magnitude_error_db:
        reasons.append("maximum magnitude error exceeds frozen acceptance threshold")

    for label, path_value, expected in (
        ("full-wave", full_wave_artifact, record.full_wave_artifact_digest),
        ("reduced", reduced_artifact, record.reduced_artifact_digest),
    ):
        if path_value is None:
            reasons.append(f"actual {label} artifact is required; manifest-only calibration is prohibited")
            continue
        path = Path(path_value)
        if not path.is_file() or path.stat().st_size == 0:
            reasons.append(f"actual {label} artifact must exist and be non-empty")
        elif artifact_digest(path).lower() != expected.lower():
            reasons.append(f"{label} artifact digest does not match retained digest")

    accepted = not reasons
    return FullWaveCalibrationDecision(
        accepted=accepted,
        reasons=tuple(reasons),
        gate_id="WS-METASURFACE-EXT-01",
        calibration_id=record.calibration_id,
        claim_control=(
            "Accepted means the frozen reduced model passed its declared numerical agreement thresholds against retained full-wave data. "
            "It does not raise the project beyond calibrated-model evidence without a separate mission-readiness update and does not prove hardware performance."
        ),
    )


def calibration_template_as_dict() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "gate_id": "WS-METASURFACE-EXT-01",
        "record": {
            "project_id": "WS-METASURFACE",
            "calibration_id": "<replace-me>",
            "solver_class": "fem|fdtd|mom|fem_bem|other_validated_maxwell",
            "solver_name": "<replace-me>",
            "solver_version": "<replace-me>",
            "geometry_digest": "<sha256>",
            "mesh_or_discretization_digest": "<sha256>",
            "material_model_digest": "<sha256>",
            "boundary_condition_digest": "<sha256>",
            "excitation_digest": "<sha256>",
            "frequency_grid_digest": "<sha256>",
            "tile_state_map_digest": "<sha256>",
            "full_wave_result_digest": "<sha256>",
            "reduced_model_digest": "<sha256>",
            "reduced_result_digest": "<sha256>",
            "full_wave_artifact_digest": "<sha256-of-retained-full-wave-data>",
            "reduced_artifact_digest": "<sha256-of-retained-reduced-data>",
            "sample_count": None,
            "phase_rmse_deg": None,
            "magnitude_rmse_db": None,
            "max_phase_error_deg": None,
            "max_magnitude_error_db": None,
            "pass_phase_rmse_deg": "<frozen-before-comparison>",
            "pass_magnitude_rmse_db": "<frozen-before-comparison>",
            "pass_max_phase_error_deg": "<frozen-before-comparison>",
            "pass_max_magnitude_error_db": "<frozen-before-comparison>",
            "source_reference": "<solver-run/evidence-package-reference>"
        },
        "required_artifacts": [
            "retained full-wave result data",
            "retained reduced-model result data",
            "geometry/mesh/material/boundary/excitation/frequency/state-map identities",
            "frozen acceptance thresholds defined before comparison"
        ],
        "claim_control": "Template only. Maxwell/control equations or a synthetic QUBO by themselves cannot satisfy full-wave calibration."
    }
