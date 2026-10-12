from pathlib import Path


def test_ready_marker_is_not_validation_marker():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_0_1_READY.md").read_text()
    assert "ready to enter protected-main review" in text
    assert "No physical, external, standards, UAS-flight, partner, or program qualification" in text
