from pathlib import Path


def test_pr_ready_marker_freezes_features():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_PR_READY_FINAL.md").read_text()
    assert "No further feature commits" in text
