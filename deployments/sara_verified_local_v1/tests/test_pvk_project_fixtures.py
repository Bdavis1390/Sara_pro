from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.physics_validation import PhysicsLayer, PhysicsVerificationRecord, ValidationState


def _records() -> list[PhysicsVerificationRecord]:
    path = Path("fixtures/pvk_representative_records_v1.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PhysicsVerificationRecord.model_validate(item) for item in payload["records"]]


def test_representative_project_records_are_bounded_and_valid():
    records = _records()

    assert {record.project_id for record in records} == {
        "WS-ALTI",
        "ADAPTIVE_METASURFACE",
        "ION_PROPULSION",
        "RESONANT_EM_PROPULSION",
    }
    assert all(record.validation_state == ValidationState.CONCEPT for record in records)
    assert all(record.claim_class <= 1 for record in records)
    assert all(record.cre1aws_approval_state.value == "not_requested" for record in records)
    assert all("no " in record.external_safe_statement.lower() for record in records)


def test_metasurface_fixture_preserves_classical_physics_boundary():
    record = next(item for item in _records() if item.project_id == "ADAPTIVE_METASURFACE")

    assert {"energy", "momentum"}.issubset(set(record.conservation_constraints))
    assert any("Maxwell" in equation.name for equation in record.governing_equations)
    assert any("mathematical decomposition" in item for item in record.assumptions)


def test_ion_fixture_does_not_inherit_external_thruster_performance():
    record = next(item for item in _records() if item.project_id == "ION_PROPULSION")

    assert record.physics_layer == PhysicsLayer.P2_ESTABLISHED_ENGINEERING
    assert {"energy", "momentum", "mass"}.issubset(set(record.conservation_constraints))
    assert "no worldshepherd-specific ion-thruster" in record.external_safe_statement.lower()
    assert any("does not inherit" in item for item in record.assumptions)


def test_anomalous_force_fixture_is_p4_and_conservation_gated():
    record = next(item for item in _records() if item.project_id == "RESONANT_EM_PROPULSION")

    assert record.physics_layer == PhysicsLayer.P4_BEYOND_STANDARD_MODEL
    assert {"energy", "momentum"}.issubset(set(record.conservation_constraints))
    assert any("F_photon" in equation.expression for equation in record.governing_equations)
    assert "no reactionless" in record.external_safe_statement.lower()
