from pathlib import Path


def test_exact_head_ci_follows_pr():
    assert "Exact-head CI follows" in (Path(__file__).parents[1] / "docs" / "WS_QX_CREATE_PR_NOW.md").read_text()
