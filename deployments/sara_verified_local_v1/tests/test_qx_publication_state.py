import json
from pathlib import Path


def test_publication_state_is_not_main_before_merge():
    state = json.loads((Path(__file__).parents[1] / "docs" / "WS_QX_0_1_PUBLICATION_STATE.json").read_text())
    assert state["repository_published_on_main"] is False
    assert state["physical_validation"] is False
    assert state["external_validation"] is False
    assert state["program_qualification"] is False
