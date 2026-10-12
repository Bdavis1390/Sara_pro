from pathlib import Path


def test_merge_policy_forbids_bypass():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_0_1_MERGE_POLICY.md").read_text()
    assert "Do not force-update main" in text
    assert "resolve the required context rather than bypassing it" in text
    assert "do not advance merely because code merged" in text
