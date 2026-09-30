from pathlib import Path


def test_exact_head_ci_determines_merge_readiness():
    assert "Exact-head CI determines merge readiness" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_FINAL.md").read_text()
