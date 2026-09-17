from pathlib import Path


def test_zero_more_feature_commits():
    assert "ZERO MORE FEATURE COMMITS" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_ZERO_MORE.md").read_text()
