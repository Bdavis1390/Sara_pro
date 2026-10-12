from pathlib import Path


def test_pr_only_transition():
    assert "before opening the PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_ONLY.md").read_text()
