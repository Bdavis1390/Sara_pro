"""Preregistered Physical Jacobian / model-discrepancy experiment planning.

The planner generates no Palace jobs by itself and chooses no perturbation amplitudes.
Every numerical value, derivative scheme, categorical alternative, and baseline context
must be registered before outputs are inspected.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


JACOBIAN_CONTRACT_VERSION = "worldshepherd.uc06-p1.physical-jacobian.v0.1"


class DiscriminatorFamily(str, Enum):
    SUBSTRATE_RELATIVE_PERMITTIVITY = "SUBSTRATE_RELATIVE_PERMITTIVITY"
    SUBSTRATE_LOSS_TANGENT = "SUBSTRATE_LOSS_TANGENT"
    SUBSTRATE_THICKNESS = "SUBSTRATE_THICKNESS"
    BRIDGE_GEOMETRY = "BRIDGE_GEOMETRY"
    PACKAGE_INDUCTANCE = "PACKAGE_INDUCTANCE"
    CONDUCTOR_THICKNESS = "CONDUCTOR_THICKNESS"
    CONDUCTOR_CONDUCTIVITY = "CONDUCTOR_CONDUCTIVITY"
    ROUGHNESS_PLATING_MODEL = "ROUGHNESS_PLATING_MODEL"
    TEMPERATURE_ELECTRICAL_PROPERTIES = "TEMPERATURE_ELECTRICAL_PROPERTIES"
    FINITE_COUPON_EDGE_GEOMETRY = "FINITE_COUPON_EDGE_GEOMETRY"


class DiscriminatorKind(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    CATEGORICAL_MODEL = "CATEGORICAL_MODEL"


class DerivativeScheme(str, Enum):
    FORWARD = "FORWARD"
    CENTRAL = "CENTRAL"


class RegisteredDiscriminator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_id: str = Field(min_length=1, max_length=128)
    family: DiscriminatorFamily
    kind: DiscriminatorKind
    units: str | None = Field(default=None, max_length=64)
    baseline_numeric_value: float | None = None
    minus_numeric_value: float | None = None
    plus_numeric_value: float | None = None
    derivative_scheme: DerivativeScheme | None = None
    baseline_model_id: str | None = Field(default=None, max_length=128)
    alternative_model_ids: list[str] = Field(default_factory=list, max_length=16)
    registered_before_output_inspection: bool

    @model_validator(mode="after")
    def validate_discriminator(self) -> "RegisteredDiscriminator":
        if not self.registered_before_output_inspection:
            raise ValueError("discriminator values/models must be preregistered before outputs")

        if self.family == DiscriminatorFamily.BRIDGE_GEOMETRY:
            allowed = {"bridge_width", "bridge_gap", "island_width", "island_length"}
            if self.parameter_id not in allowed:
                raise ValueError(
                    "BRIDGE_GEOMETRY must register one dimension at a time: "
                    + ", ".join(sorted(allowed))
                )

        if self.kind == DiscriminatorKind.CONTINUOUS:
            if self.family == DiscriminatorFamily.ROUGHNESS_PLATING_MODEL:
                raise ValueError("roughness/plating model choices must be categorical model comparisons")
            if self.baseline_numeric_value is None or self.plus_numeric_value is None:
                raise ValueError("continuous discriminator requires baseline and plus numeric values")
            if not self.units:
                raise ValueError("continuous discriminator requires explicit units")
            if self.derivative_scheme is None:
                raise ValueError("continuous discriminator requires preregistered derivative scheme")
            if self.derivative_scheme == DerivativeScheme.CENTRAL:
                if self.minus_numeric_value is None:
                    raise ValueError("CENTRAL derivative requires minus_numeric_value")
                if not (
                    self.minus_numeric_value
                    < self.baseline_numeric_value
                    < self.plus_numeric_value
                ):
                    raise ValueError("CENTRAL values must satisfy minus < baseline < plus")
            if self.derivative_scheme == DerivativeScheme.FORWARD:
                if self.minus_numeric_value is not None:
                    raise ValueError("FORWARD derivative must not register a minus value")
                if self.plus_numeric_value == self.baseline_numeric_value:
                    raise ValueError("FORWARD perturbation must differ from baseline")
            if self.baseline_model_id is not None or self.alternative_model_ids:
                raise ValueError("continuous discriminator must not mix categorical model IDs")

        if self.kind == DiscriminatorKind.CATEGORICAL_MODEL:
            if self.derivative_scheme is not None:
                raise ValueError("categorical model comparison cannot claim a derivative scheme")
            if any(
                value is not None
                for value in (
                    self.baseline_numeric_value,
                    self.minus_numeric_value,
                    self.plus_numeric_value,
                )
            ):
                raise ValueError("categorical model comparison must not carry numeric derivative values")
            if not self.baseline_model_id or not self.alternative_model_ids:
                raise ValueError("categorical model comparison requires baseline and alternatives")
            if self.baseline_model_id in self.alternative_model_ids:
                raise ValueError("baseline model cannot also be an alternative")
        return self


class JacobianCampaignRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[JACOBIAN_CONTRACT_VERSION] = JACOBIAN_CONTRACT_VERSION
    campaign_id: str = Field(min_length=1, max_length=128)
    retained_baseline_model_id: str = Field(min_length=1, max_length=128)
    retained_baseline_evidence_ref: str = Field(min_length=1, max_length=512)
    recovery_complete_evidenced: bool = False
    frozen_convergence_adjudicated: bool = False
    energy_closure_adjudicated: bool = False
    discriminators: list[RegisteredDiscriminator] = Field(min_length=1, max_length=32)
    states: tuple[Literal["LOW_C"], Literal["HIGH_C"], Literal["SAFE_OPEN"]] = (
        "LOW_C",
        "HIGH_C",
        "SAFE_OPEN",
    )
    polarizations: tuple[Literal["TE"], Literal["TM"]] = ("TE", "TM")
    angles_deg: tuple[Literal[0], Literal[30], Literal[60]] = (0, 30, 60)
    numerical_execution_authorized: Literal[False] = False
    laboratory_execution_authorized: Literal[False] = False
    scientific_gate_change: Literal[False] = False

    @model_validator(mode="after")
    def validate_registration(self) -> "JacobianCampaignRegistration":
        ids = [row.parameter_id for row in self.discriminators]
        if len(ids) != len(set(ids)):
            raise ValueError("parameter_id values must be unique")
        for row in self.discriminators:
            if (
                row.kind == DiscriminatorKind.CATEGORICAL_MODEL
                and row.baseline_model_id != self.retained_baseline_model_id
            ):
                raise ValueError(
                    "categorical discriminator baseline_model_id must equal retained baseline model"
                )
        return self


class PlannedCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str
    parameter_id: str
    condition_role: Literal["BASELINE", "MINUS", "PLUS", "ALTERNATIVE_MODEL"]
    reference_baseline_condition_id: str | None = None
    numeric_value: float | None = None
    units: str | None = None
    model_id: str | None = None
    state: Literal["LOW_C", "HIGH_C", "SAFE_OPEN"]
    polarization: Literal["TE", "TM"]
    angle_deg: Literal[0, 30, 60]


class JacobianPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    executable: Literal[False] = False
    preconditions_satisfied: bool
    unresolved_preconditions: list[str]
    baseline_condition_count: Literal[18] = 18
    perturbation_condition_count: int = Field(ge=18)
    conditions: list[PlannedCondition]
    claims_boundary: list[str]


def _numeric_token(value: float | None) -> str:
    if value is None:
        return "NONE"
    return format(value, ".17g")


def _baseline_id(state: str, pol: str, angle: int) -> str:
    return f"BASELINE:{state}:{pol}:{angle}deg"


def build_jacobian_plan(registration: JacobianCampaignRegistration) -> JacobianPlan:
    """Build a deterministic, non-executable one-factor-at-a-time condition matrix."""

    unresolved: list[str] = []
    if not registration.recovery_complete_evidenced:
        unresolved.append("A027_A054_RECOVERY_EVIDENCE")
    if not registration.frozen_convergence_adjudicated:
        unresolved.append("FROZEN_CONVERGENCE_ADJUDICATION")
    if not registration.energy_closure_adjudicated:
        unresolved.append("ENERGY_CLOSURE_ADJUDICATION")

    conditions: list[PlannedCondition] = []

    # Exactly one retained baseline matrix is shared by every discriminator.
    for state in registration.states:
        for pol in registration.polarizations:
            for angle in registration.angles_deg:
                conditions.append(
                    PlannedCondition(
                        condition_id=_baseline_id(state, pol, angle),
                        parameter_id="__RETAINED_BASELINE__",
                        condition_role="BASELINE",
                        model_id=registration.retained_baseline_model_id,
                        state=state,
                        polarization=pol,
                        angle_deg=angle,
                    )
                )

    perturbation_count = 0
    for discriminator in sorted(registration.discriminators, key=lambda row: row.parameter_id):
        if discriminator.kind == DiscriminatorKind.CONTINUOUS:
            variants: list[tuple[str, float | None, str | None]] = []
            if discriminator.derivative_scheme == DerivativeScheme.CENTRAL:
                variants.append(("MINUS", discriminator.minus_numeric_value, None))
            variants.append(("PLUS", discriminator.plus_numeric_value, None))
        else:
            variants = [
                ("ALTERNATIVE_MODEL", None, model_id)
                for model_id in sorted(discriminator.alternative_model_ids)
            ]

        for role, numeric_value, model_id in variants:
            value_token = model_id if model_id is not None else _numeric_token(numeric_value)
            for state in registration.states:
                for pol in registration.polarizations:
                    for angle in registration.angles_deg:
                        baseline_id = _baseline_id(state, pol, angle)
                        condition_id = (
                            f"{discriminator.parameter_id}:{role}:{value_token}:"
                            f"{state}:{pol}:{angle}deg"
                        )
                        conditions.append(
                            PlannedCondition(
                                condition_id=condition_id,
                                parameter_id=discriminator.parameter_id,
                                condition_role=role,
                                reference_baseline_condition_id=baseline_id,
                                numeric_value=numeric_value,
                                units=discriminator.units,
                                model_id=model_id,
                                state=state,
                                polarization=pol,
                                angle_deg=angle,
                            )
                        )
                        perturbation_count += 1

    return JacobianPlan(
        campaign_id=registration.campaign_id,
        preconditions_satisfied=not unresolved,
        unresolved_preconditions=unresolved,
        perturbation_condition_count=perturbation_count,
        conditions=conditions,
        claims_boundary=[
            "PLAN_ONLY_NOT_EXECUTION_AUTHORIZATION",
            "ONE_SHARED_RETAINED_BASELINE_MATRIX",
            "ONE_DISCRIMINATOR_AT_A_TIME",
            "NO_PERTURBATION_AMPLITUDE_CHOSEN_BY_SOFTWARE",
            "CATEGORICAL_MODEL_COMPARISONS_ARE_NOT_JACOBIANS",
            "NO_NUMERICAL_OUTPUT_INSPECTED_TO_CHOOSE_VALUES",
            "NO_LAB_EXECUTION_AUTHORIZED",
            "NO_SCIENTIFIC_GATE_CHANGE",
        ],
    )
