from pathlib import Path


def test_content_complete_moves_to_ci():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_RC1_CONTENT_COMPLETE.md").read_text()
    assert "Open PR; run exact-head CI" in text
