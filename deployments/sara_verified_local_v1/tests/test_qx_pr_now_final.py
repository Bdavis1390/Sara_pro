from pathlib import Path


def test_create_it():
    assert "Create it" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_NOW_FINAL.md").read_text()
