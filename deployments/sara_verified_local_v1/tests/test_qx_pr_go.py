from pathlib import Path


def test_pr_go():
    assert "PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_GO.md").read_text()
