from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class ModelFamily(str, Enum):
    ENERGY_MAGNITUDE = "H0_ENERGY_MAGNITUDE"
    SINGLE_FREQUENCY = "H1_SINGLE_FREQUENCY"
    ORGANIZED_DYNAMICS = "H2_ORGANIZED_DYNAMICS"
    ORGANIZED_ENERGY = "H3_ORGANIZED_ENERGY"

@dataclass(frozen=True)
class ConsciousnessFeatureVector:
    metabolism: float | None = None
    total_power: float | None = None
    selected_frequency_power: float | None = None
    complexity: float | None = None
    criticality: float | None = None
    connectivity: float | None = None
    pci: float | None = None
    fdt_violation: float | None = None
    entropy_production: float | None = None
    dynamical_asymmetry: float | None = None

def feature_names_for_model(model: ModelFamily) -> set[str]:
    if model == ModelFamily.ENERGY_MAGNITUDE:
        return {"metabolism", "total_power"}
    if model == ModelFamily.SINGLE_FREQUENCY:
        return {"selected_frequency_power"}
    if model == ModelFamily.ORGANIZED_DYNAMICS:
        return {"complexity", "criticality", "connectivity", "pci", "fdt_violation"}
    if model == ModelFamily.ORGANIZED_ENERGY:
        return {
            "metabolism",
            "total_power",
            "complexity",
            "criticality",
            "connectivity",
            "pci",
            "fdt_violation",
            "entropy_production",
            "dynamical_asymmetry",
        }
    raise ValueError(model)

def available_features(
    vector: ConsciousnessFeatureVector,
    model: ModelFamily,
) -> dict[str, float]:
    requested = feature_names_for_model(model)
    out = {}
    for name in requested:
        value = getattr(vector, name)
        if value is not None:
            out[name] = value
    return out

@dataclass(frozen=True)
class ModelResult:
    family: ModelFamily
    held_out_score: float
    calibration_error: float
    conditions: tuple[str, ...]
    evidence_ref: str

def compare_models(results: list[ModelResult]) -> dict:
    if not results:
        raise ValueError("results required")
    ranked = sorted(
        results,
        key=lambda r: (-r.held_out_score, r.calibration_error),
    )
    return {
        "best_family": ranked[0].family.value,
        "ranking": [
            {
                "family": r.family.value,
                "held_out_score": r.held_out_score,
                "calibration_error": r.calibration_error,
            }
            for r in ranked
        ],
        "claim_ceiling": "COMPARATIVE_MODEL_SUPPORT_ONLY",
    }

def organized_energy_supported_over_energy_only(
    results: list[ModelResult],
    minimum_score_margin: float,
) -> bool:
    by_family = {r.family: r for r in results}
    h0 = by_family.get(ModelFamily.ENERGY_MAGNITUDE)
    h3 = by_family.get(ModelFamily.ORGANIZED_ENERGY)
    if h0 is None or h3 is None:
        return False
    return (
        h3.held_out_score - h0.held_out_score >= minimum_score_margin
        and h3.calibration_error <= h0.calibration_error
    )
