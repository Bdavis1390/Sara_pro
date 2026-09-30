from pathlib import Path


def test_ready_to_create_pr():
    assert "READY TO CREATE PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_READY_TO_CREATE.md").read_text()
