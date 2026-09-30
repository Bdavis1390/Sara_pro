from pathlib import Path


def test_feature_freeze_moves_directly_to_pr():
    assert "Proceed directly to PR creation" in (Path(__file__).parents[1] / "docs" / "WS_QX_NO_MORE_FEATURES.md").read_text()
