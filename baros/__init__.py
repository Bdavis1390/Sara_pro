"""BAROS research reference package. Non-clinical; not for patient care."""

from .dose import dose_from_influence, hard_max_constraints
from .models import logistic_ntcp, lq_survival, poisson_tcp, weighted_mean
from .pipeline import SCHEMA_VERSION, SyntheticCase, default_synthetic_case, run_synthetic_pipeline
from .reference_optimizer import OptimizationResult, optimize_synthetic, tumor_survival_objective

__all__ = [
    "dose_from_influence",
    "hard_max_constraints",
    "logistic_ntcp",
    "lq_survival",
    "poisson_tcp",
    "weighted_mean",
    "SCHEMA_VERSION",
    "SyntheticCase",
    "default_synthetic_case",
    "run_synthetic_pipeline",
    "OptimizationResult",
    "optimize_synthetic",
    "tumor_survival_objective",
]
