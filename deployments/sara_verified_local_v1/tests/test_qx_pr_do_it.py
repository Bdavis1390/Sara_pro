from pathlib import Path


def test_create_the_pr():
    assert "Create the PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_DO_IT.md").read_text()
