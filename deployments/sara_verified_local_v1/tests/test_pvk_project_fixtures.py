from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.physics_validation import PhysicsVerificationRecord, ValidationState


def test_representative_project_records_are_bounded_and_valid():
    path = Path("fixtures/pvk_representative_records_v1.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = [PhysicsVerificationRecord.model_validate(item) for item in payload["records"]]

    assert {record.project_id for record in records} == {"WS-ALTI", "ADAPTIVE_METASURFACE"}
    assert all(record.validation_state == ValidationState.CONCEPT for record in records)
    assert all(record.claim_class <= 1 for record in records)
    assert all(record.cre1aws_approval_state.value == "not_requested" for record in records)
    assert all("no " in record.external_safe_statement.lower() for record in records)


def test_metasurface_fixture_preserves_classical_physics_boundary():
    payload = json.loads(
        Path("fixtures/pvk_representative_records_v1.json").read_text(encoding="utf-8")
    )
    metasurface = next(item for item in payload["records"] if item["project_id"] == "ADAPTIVE_METASURFACE")
    record = PhysicsVerificationRecord.model_validate(metasurface)

    assert {"energy", "momentum"}.issubset(set(record.conservation_constraints))
    assert any("Maxwell" in equation.name for equation in record.governing_equations)
    assert any("mathematical decomposition" in item for item in record.assumptions)
