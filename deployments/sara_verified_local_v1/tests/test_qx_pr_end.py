from pathlib import Path


def test_pr_is_next():
    assert "PR next" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_END.md").read_text()
