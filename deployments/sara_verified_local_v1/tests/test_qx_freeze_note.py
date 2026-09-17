from pathlib import Path


def test_freeze_note_requires_fresh_ci_after_correction():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_FREEZE_SHA_NOTE.md").read_text()
    assert "requires fresh checks on the new head" in text
