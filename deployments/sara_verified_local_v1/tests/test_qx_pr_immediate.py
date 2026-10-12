from pathlib import Path


def test_immediate_action_is_pr():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_PR_IMMEDIATE.md").read_text()
    assert "Create pull request" in text
    assert "No further feature commits" in text
