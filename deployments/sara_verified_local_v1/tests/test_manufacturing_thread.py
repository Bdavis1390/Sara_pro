from __future__ import annotations

import pytest

from worldshepherd_sara.manufacturing_thread import (
    BuildStep,
    ManufacturingDigitalThread,
    MaterialLot,
    ProcessConfiguration,
    SpecimenRecord,
)


def test_manufacturing_digital_thread_preserves_material_process_specimen_lineage():
    thread = ManufacturingDigitalThread(
        thread_id="WS-MFG-SYNTH-001",
        material_lots=[MaterialLot(lot_id="LOT-1", material_designation="Synthetic Al-Ti-Mg-Sc-Zr research lot")],
        process_configurations=[
            ProcessConfiguration(
                configuration_id="CFG-1",
                process_family="DED_SYNTHETIC",
                machine_id="SIMULATED-MACHINE",
                parameters={"laser_power_w": 500, "travel_speed_mm_s": 10},
            )
        ],
        build_steps=[BuildStep(step_id="STEP-1", material_lot_ids=["LOT-1"], configuration_id="CFG-1")],
        specimens=[SpecimenRecord(specimen_id="COUPON-1", build_step_ids=["STEP-1"])],
        claims_boundary=["Digital thread only; no material-property or process-performance claim"],
    )
    assert thread.qualification_state() == "DIGITAL_THREAD_ONLY"
    assert thread.digest().startswith("sha256:")


def test_manufacturing_thread_requires_resolvable_references():
    with pytest.raises(ValueError):
        ManufacturingDigitalThread(
            thread_id="BAD",
            material_lots=[],
            process_configurations=[],
            build_steps=[BuildStep(step_id="S1", material_lot_ids=["MISSING"], configuration_id="NOPE")],
        )


def test_physical_measurement_state_requires_explicit_measurement_reference_and_flag():
    thread = ManufacturingDigitalThread(
        thread_id="WS-MFG-MEASURED-SYNTH",
        material_lots=[MaterialLot(lot_id="LOT-1", material_designation="Synthetic alloy")],
        process_configurations=[ProcessConfiguration(configuration_id="CFG-1", process_family="DED_SYNTHETIC", machine_id="M1")],
        build_steps=[BuildStep(step_id="STEP-1", material_lot_ids=["LOT-1"], configuration_id="CFG-1")],
        specimens=[
            SpecimenRecord(
                specimen_id="COUPON-1",
                build_step_ids=["STEP-1"],
                measurement_artifact_digests=["sha256:measurement-placeholder"],
                physical_validation_performed=True,
            )
        ],
    )
    assert thread.qualification_state() == "PHYSICAL_MEASUREMENT_REFERENCED"
