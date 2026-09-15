from __future__ import annotations

import pytest

from worldshepherd_sara.evidence_contract import EvidenceValidationError
from worldshepherd_sara.evidence_material import validate_material_record
from worldshepherd_sara.evidence_registry import EvidenceReferenceError, EvidenceRegistry


def material_payload(material_batch_id="MAT-WSALTI-001", batch_role="FEEDSTOCK"):
    return {
        "material_batch_id": material_batch_id,
        "material_system": "WS-AlTi candidate architecture",
        "batch_role": batch_role,
        "composition": {
            "basis": "WT_PERCENT",
            "constituents": [
                {"species": "Al", "fraction": 91.9},
                {"species": "Ti", "fraction": 6.0},
                {"species": "Mg", "fraction": 1.5},
                {"species": "Sc", "fraction": 0.2},
                {"species": "Zr", "fraction": 0.4},
            ],
        },
        "feedstock_ids": [],
        "process_history": [],
        "microstructure_observations": [],
        "properties": [],
        "component_links": [],
        "review_state": "DRAFT",
    }


def test_candidate_composition_is_structurally_valid_without_property_claims():
    payload = material_payload()
    assert validate_material_record(payload)["properties"] == []


def test_percentage_composition_must_close():
    payload = material_payload()
    payload["composition"]["constituents"][0]["fraction"] = 90.0
    with pytest.raises(EvidenceValidationError, match="sum to 100"):
        validate_material_record(payload)


def test_measured_property_requires_source_and_uncertainty():
    payload = material_payload()
    payload["properties"] = [
        {
            "property_id": "PROP-001",
            "name": "test_property",
            "value": 1.0,
            "units": "arb",
            "evidence_class": "MEASURED",
            "conditions": {},
            "source_record_ids": [],
        }
    ]
    with pytest.raises(EvidenceValidationError, match="requires source_record_ids"):
        validate_material_record(payload)


def test_simulated_property_remains_explicitly_simulated(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    payload = material_payload()
    payload["properties"] = [
        {
            "property_id": "PROP-SIM-001",
            "name": "test_property",
            "value": 1.0,
            "units": "arb",
            "evidence_class": "SIMULATED",
            "conditions": {"purpose": "schema test only"},
            "source_record_ids": [],
        }
    ]
    envelope = registry.append("material", payload, actor="operator")
    assert envelope["record"]["properties"][0]["evidence_class"] == "SIMULATED"


def test_deposit_feedstock_lineage_must_resolve_to_material_record(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    registry.append("material", material_payload("MAT-FEED-001", "FEEDSTOCK"), actor="operator")
    deposit = material_payload("MAT-DEPOSIT-001", "DEPOSIT")
    deposit["feedstock_ids"] = ["MAT-FEED-001"]
    deposit["process_history"] = [
        {
            "step_id": "DED-001",
            "process_type": "DED candidate process record",
            "parameters": {"status": "test fixture; not a validated process window"},
            "configuration_digest": "sha256:process-placeholder",
        }
    ]
    envelope = registry.append("material", deposit, actor="operator")
    assert envelope["record"]["feedstock_ids"] == ["MAT-FEED-001"]


def test_missing_feedstock_record_is_rejected(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    deposit = material_payload("MAT-DEPOSIT-001", "DEPOSIT")
    deposit["feedstock_ids"] = ["MAT-MISSING"]
    with pytest.raises(EvidenceReferenceError, match="does not exist"):
        registry.append("material", deposit, actor="operator")
