from pathlib import Path


def test_rc1_locked_for_pr():
    assert "Proceed to pull request" in (Path(__file__).parents[1] / "docs" / "WS_QX_RC1_LOCK.md").read_text()
