import json
from pathlib import Path


def test_profile_registry_has_no_physical_validation_by_default():
    path = Path(__file__).parents[1] / "docs" / "WS_QX_PROFILE_REGISTRY_0_1.json"
    registry = json.loads(path.read_text())
    assert registry["profiles"]
    assert all(profile["physical_validation"] is False for profile in registry["profiles"])
