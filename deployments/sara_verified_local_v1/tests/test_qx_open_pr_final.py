from pathlib import Path


def test_open_now():
    assert "Open now" in (Path(__file__).parents[1] / "docs" / "WS_QX_OPEN_PR_FINAL.md").read_text()
