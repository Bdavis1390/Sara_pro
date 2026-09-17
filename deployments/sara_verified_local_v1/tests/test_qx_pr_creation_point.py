from pathlib import Path


def test_no_features_beyond_creation_point():
    assert "No feature changes beyond this point" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_CREATION_POINT.md").read_text()
