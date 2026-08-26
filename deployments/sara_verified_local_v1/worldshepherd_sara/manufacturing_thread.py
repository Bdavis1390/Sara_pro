from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from .qualification import canonical_digest


class MaterialLot(BaseModel):
    lot_id: str = Field(min_length=1)
    material_designation: str = Field(min_length=1)
    supplier: str | None = None
    certificate_digest: str | None = None
    composition_evidence_ref: str | None = None


class ProcessConfiguration(BaseModel):
    configuration_id: str = Field(min_length=1)
    process_family: str = Field(min_length=1)
    machine_id: str = Field(min_length=1)
    software_version: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    configuration_artifact_digest: str | None = None


class BuildStep(BaseModel):
    step_id: str = Field(min_length=1)
    material_lot_ids: list[str] = Field(default_factory=list)
    configuration_id: str = Field(min_length=1)
    start_utc: str | None = None
    end_utc: str | None = None
    telemetry_artifact_digests: list[str] = Field(default_factory=list)
    operator: str | None = None


class SpecimenRecord(BaseModel):
    specimen_id: str = Field(min_length=1)
    build_step_ids: list[str] = Field(default_factory=list)
    geometry_ref: str | None = None
    measurement_artifact_digests: list[str] = Field(default_factory=list)
    physical_validation_performed: bool = False


class ManufacturingDigitalThread(BaseModel):
    thread_id: str = Field(min_length=1)
    material_lots: list[MaterialLot] = Field(default_factory=list)
    process_configurations: list[ProcessConfiguration] = Field(default_factory=list)
    build_steps: list[BuildStep] = Field(default_factory=list)
    specimens: list[SpecimenRecord] = Field(default_factory=list)
    claims_boundary: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_must_resolve(self) -> "ManufacturingDigitalThread":
        lots = {item.lot_id for item in self.material_lots}
        configs = {item.configuration_id for item in self.process_configurations}
        steps = {item.step_id for item in self.build_steps}
        if len(lots) != len(self.material_lots):
            raise ValueError("duplicate material lot id")
        if len(configs) != len(self.process_configurations):
            raise ValueError("duplicate process configuration id")
        if len(steps) != len(self.build_steps):
            raise ValueError("duplicate build step id")
        for step in self.build_steps:
            unknown_lots = set(step.material_lot_ids) - lots
            if unknown_lots:
                raise ValueError(f"build step {step.step_id} references unknown material lots: {sorted(unknown_lots)}")
            if step.configuration_id not in configs:
                raise ValueError(f"build step {step.step_id} references unknown configuration")
        for specimen in self.specimens:
            unknown_steps = set(specimen.build_step_ids) - steps
            if unknown_steps:
                raise ValueError(f"specimen {specimen.specimen_id} references unknown build steps: {sorted(unknown_steps)}")
        return self

    def digest(self) -> str:
        return canonical_digest(self)

    def qualification_state(self) -> str:
        if any(specimen.physical_validation_performed and specimen.measurement_artifact_digests for specimen in self.specimens):
            return "PHYSICAL_MEASUREMENT_REFERENCED"
        return "DIGITAL_THREAD_ONLY"
