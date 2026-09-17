from pathlib import Path


def test_handoff_requires_exact_head_and_no_bypass():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_0_1_HANDOFF.md").read_text()
    assert "exact head SHA" in text
    assert "never bypass required checks" in text
    assert "A merge does not change physical/external/program claim states" in text
