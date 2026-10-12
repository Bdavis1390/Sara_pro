from pathlib import Path


def test_now_pr_marker():
    assert "NOW: PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_NOW_PR.md").read_text()
