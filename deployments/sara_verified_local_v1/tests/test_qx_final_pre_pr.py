from pathlib import Path


def test_final_pre_pr_moves_to_ci():
    assert "exact-head CI next" in (Path(__file__).parents[1] / "docs" / "WS_QX_FINAL_PRE_PR.md").read_text()
