from pathlib import Path


def test_pr_now_uses_reported_head():
    assert "exact reported head" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_NOW.md").read_text()
