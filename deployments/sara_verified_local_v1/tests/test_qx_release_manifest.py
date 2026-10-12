import json
from pathlib import Path


def test_release_manifest_does_not_claim_unearned_validation():
    path = Path(__file__).parents[1] / "docs" / "WS_QX_RELEASE_MANIFEST_0_1.json"
    manifest = json.loads(path.read_text())
    assert manifest["physical_validation"] is False
    assert manifest["external_validation"] is False
    assert manifest["program_qualification"] is False
    assert manifest["standards_conformance"] is False
    assert manifest["historical_g3_merged"] is False
