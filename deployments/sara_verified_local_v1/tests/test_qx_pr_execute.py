from pathlib import Path


def test_open_pr_after_commit():
    assert "Open PR after this commit" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_EXECUTE.md").read_text()
