from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .qualification import ForecastHorizon
from .readiness import ReadinessRung


class CapabilityHorizonRecord(BaseModel):
    horizon_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    horizon: ForecastHorizon
    target_rung: ReadinessRung
    prerequisite_rung: ReadinessRung
    requirement_delta_ids: list[str] = Field(default_factory=list)
    build_actions: list[str] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)
    partner_actions: list[str] = Field(default_factory=list)
    evidence_targets: list[str] = Field(default_factory=list)
    blocking_conditions: list[str] = Field(default_factory=list)
    forecast_only: bool = False

    @model_validator(mode="after")
    def target_must_not_skip_prerequisite(self) -> "CapabilityHorizonRecord":
        if self.target_rung < self.prerequisite_rung:
            raise ValueError("target rung cannot be below prerequisite rung")
        if self.target_rung > self.prerequisite_rung + 1:
            raise ValueError("horizon plan may advance at most one readiness rung per evidence gate")
        return self

    def actionable(self) -> bool:
        return bool(self.build_actions or self.experiments or self.partner_actions)


class CapabilityHorizonPortfolio(BaseModel):
    records: list[CapabilityHorizonRecord] = Field(default_factory=list)

    def by_horizon(self, horizon: ForecastHorizon) -> list[CapabilityHorizonRecord]:
        return [record for record in self.records if record.horizon == horizon]

    def immediate_actions(self) -> list[str]:
        actions: list[str] = []
        for record in self.by_horizon(ForecastHorizon.D0_90):
            actions.extend(record.build_actions)
            actions.extend(record.experiments)
            actions.extend(record.partner_actions)
        return sorted(set(actions))
