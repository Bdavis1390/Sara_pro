"""Bind synthetic/model-research identifiability calculations to BAROS state.

This module does NOT validate biological imaging, infer real tumor hypoxia,
calibrate model assumptions, or establish clinical treatment safety.
A caller must supply a legally permitted and scientifically meaningful
Jacobian, observation model and real-world measurement protocol.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import re
from typing import Sequence

from .closed_loop import BiologicalState
from .model_assurance import IdentifiabilityAssessment, assess_local_identifiability


_HEX = re.compile(r"^[0-9a-f]{64}$")


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class BoundIdentifiabilityState:
    state: BiologicalState
    assessment: IdentifiabilityAssessment
    jacobian_sha256: str
    reported_source_sha256: str
    binding_sha256: str

    @property
    def qualified_by_local_identifiability(self) -> bool:
        return self.assessment.locally_identifiable


def bind_research_identifiability(
    *,
    state: BiologicalState,
    jacobian: Sequence[Sequence[float]],
    parameter_names: Sequence[str],
    reported_source_sha256: str,
    condition_limit: float = 1e8,
) -> BoundIdentifiabilityState:
    """Replace a caller-provided flag with computed local identifiability.

    The calculated SVD status is valid *only for the supplied sensitivity
    matrix and threshold*, not for an unvalidated biologic model or patient.
    """
    state.validate()
    if not isinstance(reported_source_sha256, str) or not _HEX.fullmatch(reported_source_sha256):
        raise ValueError("reported_source_sha256 must be a lowercase 64-character digest")
    rows = tuple(tuple(float(v) for v in row) for row in jacobian)
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("jacobian contains non-finite values")
    names = tuple(str(v).strip() for v in parameter_names)
    assessment = assess_local_identifiability(
        rows,
        parameter_names=names,
        condition_limit=condition_limit,
    )
    bound_state = replace(state, model_identifiable=assessment.locally_identifiable)
    payload = {
        "state": asdict(bound_state),
        "assessment": asdict(assessment),
        "jacobian": rows,
        "parameters": names,
        "condition_limit": condition_limit,
        "reported_source_sha256": reported_source_sha256,
        "nonclinical": True,
    }
    return BoundIdentifiabilityState(
        state=bound_state,
        assessment=assessment,
        jacobian_sha256=_hash({"jacobian": rows, "parameters": names}),
        reported_source_sha256=reported_source_sha256,
        binding_sha256=_hash(payload),
    )
