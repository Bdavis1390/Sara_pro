from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.physics_validation import PhysicsLayer, PhysicsVerificationRecord, ValidationState


def _records() -> list[PhysicsVerificationRecord]:
    payload = json.loads(
        Path("fixtures/pvk_representative_records_wave2_v1.json").read_text(
            encoding="utf-8"
        )
    )
    return [PhysicsVerificationRecord.model_validate(item) for item in payload["records"]]


def test_wave2_records_are_concept_stage_and_bounded():
    records = _records()
    assert {record.project_id for record in records} == {
        "HELIOS_LINK",
        "TIDELENS_SPECULAR_MIST",
        "AEROSHEPHERD",
        "BAROS",
    }
    assert all(record.validation_state == ValidationState.CONCEPT for record in records)
    assert all(record.claim_class <= 1 for record in records)
    assert all(record.cre1aws_approval_state.value == "not_requested" for record in records)
    assert all(record.physics_layer == PhysicsLayer.P2_ESTABLISHED_ENGINEERING for record in records)


def test_helios_record_keeps_power_boundaries_explicit():
    record = next(item for item in _records() if item.project_id == "HELIOS_LINK")
    assert any("eta_e2e" in equation.expression for equation in record.governing_equations)
    assert {"energy", "momentum"}.issubset(set(record.conservation_constraints))
    assert "no HELIOS-LINK-specific" in record.external_safe_statement


def test_tidelines_record_separates_measurement_classes():
    record = next(
        item for item in _records() if item.project_id == "TIDELENS_SPECULAR_MIST"
    )
    assert any("Synthetic-data" in item for item in record.assumptions)
    assert any("far-field RCS" in item for item in record.assumptions)
    assert "no Worldshepherd-specific" in record.external_safe_statement


def test_aeroshepherd_record_blocks_component_to_vehicle_maturity_jump():
    record = next(item for item in _records() if item.project_id == "AEROSHEPHERD")
    assert any("Component maturity" in item for item in record.assumptions)
    assert {"energy", "momentum", "mass"}.issubset(set(record.conservation_constraints))
    assert "no complete-vehicle" in record.external_safe_statement


def test_baros_record_is_research_only():
    record = next(item for item in _records() if item.project_id == "BAROS")
    assert "No patient-specific clinical use" in " ".join(record.assumptions)
    assert any("Research-only" in item for item in record.hazard_controls)
    assert "no patient-specific clinical validity" in record.external_safe_statement
