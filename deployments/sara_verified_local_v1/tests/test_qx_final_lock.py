from pathlib import Path


def test_final_lock_is_pr_only():
    assert "PR creation only" in (Path(__file__).parents[1] / "docs" / "WS_QX_FINAL_LOCK.md").read_text()
