from pathlib import Path


def test_last_marker_says_pr_next():
    assert "PR next" in (Path(__file__).parents[1] / "docs" / "WS_QX_LAST_MARKER.md").read_text()
