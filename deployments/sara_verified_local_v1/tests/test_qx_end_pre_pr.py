from pathlib import Path


def test_end_pre_pr_proceeds_to_pr():
    assert "Proceed to PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_END_PRE_PR.md").read_text()
