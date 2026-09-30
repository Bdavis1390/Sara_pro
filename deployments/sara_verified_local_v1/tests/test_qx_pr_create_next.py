from pathlib import Path


def test_next_action_is_create_pr():
    assert "NEXT ACTION: CREATE PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_CREATE_NEXT.md").read_text()
