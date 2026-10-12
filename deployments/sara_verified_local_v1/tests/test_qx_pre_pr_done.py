from pathlib import Path


def test_pr_creation_follows_immediately():
    assert "PR creation follows immediately" in (Path(__file__).parents[1] / "docs" / "WS_QX_PRE_PR_DONE.md").read_text()
