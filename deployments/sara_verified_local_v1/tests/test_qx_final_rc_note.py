from pathlib import Path


def test_final_rc_limits_changes_to_corrective_work():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_0_1_FINAL_RC_NOTE.md").read_text()
    assert "corrective changes" in text
    assert "merge preparation" in text
