from pathlib import Path


def test_create_pr_marker():
    assert "against protected main now" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_CREATE.md").read_text()
