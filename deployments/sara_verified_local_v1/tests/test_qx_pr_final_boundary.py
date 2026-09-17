from pathlib import Path


def test_pr_creation_follows_boundary():
    assert "PR creation follows this commit" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_FINAL_BOUNDARY.md").read_text()
