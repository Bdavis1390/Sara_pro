from pathlib import Path


def test_create_pr_action():
    assert "CREATE PR ACTION" in (Path(__file__).parents[1] / "docs" / "WS_QX_CREATE_PR_ACTION.md").read_text()
