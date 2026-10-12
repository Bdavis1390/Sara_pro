import json
from pathlib import Path


def test_qx_schema_keeps_high_order_claims_explicit():
    path = Path(__file__).parents[1] / "fixtures" / "ws_qx_evidence_01_schema.json"
    schema = json.loads(path.read_text())
    claims = schema["properties"]["claims"]
    required = set(claims["required"])
    assert {"physical_validation", "external_validation", "standards_conformance", "program_qualification"} <= required


def test_qx_schema_requires_physical_interlock_fields():
    path = Path(__file__).parents[1] / "fixtures" / "ws_qx_evidence_01_schema.json"
    schema = json.loads(path.read_text())
    required = set(schema["required"])
    assert {"physical_io_observed", "human_safety_controls_verified", "run_complete"} <= required
