"""UC06-P1 D5 evidence-ingestion and sparse-interrogation contracts.

This module intentionally contains no D5 scientific result values.  Until a sealed
local D5 receipt is ingested, the public status remains PENDING.  Sparse-frequency
selections are diagnostic candidates only and can never authorize hardware action.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
D5_CONTRACT_VERSION = "worldshepherd.uc06-p1.d5.v0.1"


class D5Status(str, Enum):
    PENDING = "PENDING"
    INGESTED_DIAGNOSTIC = "INGESTED_DIAGNOSTIC"


class D5InteractionEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal_component: int = Field(ge=1, le=3)
    effect: Literal[
        "STATE",
        "POLARIZATION",
        "ANGLE",
        "STATE_X_POLARIZATION",
        "STATE_X_ANGLE",
        "POLARIZATION_X_ANGLE",
        "STATE_X_POLARIZATION_X_ANGLE",
    ]
    fraction_of_pc_variance: float = Field(ge=0.0, le=1.0)


class D5SparseFrequencySelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["UNCONSTRAINED", "SPACED_0P10GHZ", "TASK_SPECIFIC"]
    frequencies_GHz: list[float] = Field(min_length=1, max_length=8)
    pairwise_distance_correlation: float | None = Field(default=None, ge=-1.0, le=1.0)
    normalized_scaled_stress: float | None = Field(default=None, ge=0.0)
    task_metric: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_frequencies(self) -> "D5SparseFrequencySelection":
        if len(set(self.frequencies_GHz)) != len(self.frequencies_GHz):
            raise ValueError("sparse frequencies must be unique")
        if any(f < 9.2 or f > 10.8 for f in self.frequencies_GHz):
            raise ValueError("sparse frequencies must remain inside the frozen 9.2-10.8 GHz band")
        if self.mode == "SPACED_0P10GHZ":
            ordered = sorted(self.frequencies_GHz)
            if any((b - a) < 0.10 - 1e-12 for a, b in zip(ordered, ordered[1:])):
                raise ValueError("SPACED_0P10GHZ selections must preserve 0.10 GHz spacing")
        return self


class D5EvidencePackage(BaseModel):
    """Machine-readable representation of a future sealed D5 diagnostic receipt."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[D5_CONTRACT_VERSION] = D5_CONTRACT_VERSION
    status: Literal[D5Status.INGESTED_DIAGNOSTIC] = D5Status.INGESTED_DIAGNOSTIC
    source_receipt: str = Field(min_length=1, max_length=512)
    source_receipt_sha256: str
    evidence_integrity_pass: Literal[True] = True
    active_recovery_touched: Literal[False] = False
    scientific_gate_change: Literal[False] = False
    overall_convergence: Literal["NOT_ADJUDICATED"] = "NOT_ADJUDICATED"
    interaction_effects: list[D5InteractionEffect] = Field(min_length=21, max_length=21)
    sparse_frequency_selections: list[D5SparseFrequencySelection] = Field(default_factory=list, max_length=32)
    claims_boundary: list[str] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_package(self) -> "D5EvidencePackage":
        if not _SHA256_RE.fullmatch(self.source_receipt_sha256):
            raise ValueError("source_receipt_sha256 must be a lowercase SHA-256 hex digest")

        # Structural closure check only: D5 preregisters seven orthogonal descriptive
        # effects for each of PC1-PC3.  This is not a scientific acceptance threshold.
        for pc in (1, 2, 3):
            rows = [r for r in self.interaction_effects if r.principal_component == pc]
            if len(rows) != 7:
                raise ValueError(f"PC{pc} must contain exactly seven preregistered effects")
            if len({r.effect for r in rows}) != 7:
                raise ValueError(f"PC{pc} contains duplicate or missing effects")
            if abs(sum(r.fraction_of_pc_variance for r in rows) - 1.0) > 1e-6:
                raise ValueError(f"PC{pc} descriptive variance fractions do not close to unity")
        return self


class D5StatusSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[D5_CONTRACT_VERSION] = D5_CONTRACT_VERSION
    status: Literal[D5Status.PENDING] = D5Status.PENDING
    sealed_result_ingested: Literal[False] = False
    result_values_available: Literal[False] = False
    active_recovery_touched: Literal[False] = False
    scientific_gate_change: Literal[False] = False
    overall_convergence: Literal["NOT_ADJUDICATED"] = "NOT_ADJUDICATED"
    claims_boundary: list[str]


class SparseInterrogationReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    d5_sealed_evidence_ingested: bool = False
    pairwise_geometry_preserved_on_held_out_data: bool = False
    task_discriminability_preserved_on_held_out_data: bool = False
    measurement_repeatability_validated: bool = False
    hardware_measurement_validated: bool = False
    medium_fine_convergence_passed: bool = False
    energy_closure_passed: bool = False
    prime_review_complete: bool = False


class SparseInterrogationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible_for_operational_interrogation: bool
    hardware_action_authorized: Literal[False] = False
    unresolved_gates: list[str]
    rationale_codes: list[str]


def evaluate_sparse_interrogation_readiness(
    readiness: SparseInterrogationReadiness,
) -> SparseInterrogationDecision:
    """Fail closed until every sparse-interrogation evidence gate is explicit."""

    required = {
        "D5_SEALED_EVIDENCE": readiness.d5_sealed_evidence_ingested,
        "HELD_OUT_GEOMETRY": readiness.pairwise_geometry_preserved_on_held_out_data,
        "HELD_OUT_TASKS": readiness.task_discriminability_preserved_on_held_out_data,
        "REPEATABILITY": readiness.measurement_repeatability_validated,
        "HARDWARE_MEASUREMENT": readiness.hardware_measurement_validated,
        "MEDIUM_FINE_CONVERGENCE": readiness.medium_fine_convergence_passed,
        "ENERGY_CLOSURE": readiness.energy_closure_passed,
        "PRIME_REVIEW": readiness.prime_review_complete,
    }
    unresolved = [name for name, passed in required.items() if not passed]
    eligible = not unresolved
    return SparseInterrogationDecision(
        eligible_for_operational_interrogation=eligible,
        unresolved_gates=unresolved,
        rationale_codes=(
            ["ELIGIBLE_FOR_OPERATIONAL_INTERROGATION_REVIEW"]
            if eligible
            else ["FAIL_CLOSED", *[f"MISSING_{name}" for name in unresolved]]
        ),
    )


def pending_d5_status() -> D5StatusSummary:
    return D5StatusSummary(
        claims_boundary=[
            "NO_D5_RESULT_VALUES_INGESTED",
            "NO_INTERACTION_ATTRIBUTION_CLAIM",
            "NO_SPARSE_FREQUENCY_RECOMMENDATION",
            "NO_HELD_OUT_GENERALIZATION_CLAIM",
            "NO_HARDWARE_OBSERVABILITY_CLAIM",
            "NO_SCIENTIFIC_GATE_CHANGE",
            "NO_HARDWARE_ACTION",
        ]
    )


router = APIRouter(prefix="/v1/em/uc06/d5", tags=["em-d5"])


@router.get("/status", response_model=D5StatusSummary)
def d5_status() -> D5StatusSummary:
    """Return PENDING until a separately sealed local D5 result is ingested."""

    return pending_d5_status()


@router.get("/contract")
def d5_contract() -> dict[str, object]:
    return {
        "contract_version": D5_CONTRACT_VERSION,
        "read_only": True,
        "current_status": D5Status.PENDING.value,
        "expected_inputs": [
            "sealed local D5 receipt",
            "receipt SHA-256",
            "21 PC/effect variance rows",
            "optional diagnostic sparse-frequency selections",
        ],
        "structural_checks_are_not_scientific_thresholds": True,
        "sparse_interrogation_requires_independent_validation": True,
        "hardware_actions": False,
    }
