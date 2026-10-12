from pathlib import Path


def test_transition_complete():
    assert "Open the pull request now" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_TRANSITION_COMPLETE.md").read_text()
