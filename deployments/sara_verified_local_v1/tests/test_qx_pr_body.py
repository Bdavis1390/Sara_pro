from pathlib import Path


def test_pr_narrative_keeps_evidence_levels_separate():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_0_1_PR_BODY.md").read_text()
    assert "Internal qualification does not imply physical validation" in text
    assert "physical validation does not imply external validation" in text
    assert "solicitation alignment does not imply program eligibility" in text
