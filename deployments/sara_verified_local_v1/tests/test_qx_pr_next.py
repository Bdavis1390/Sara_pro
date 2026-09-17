from pathlib import Path


def test_next_operation_is_pr_creation():
    assert "Pull request creation" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_NEXT.md").read_text()
