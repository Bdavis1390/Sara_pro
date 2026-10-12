from pathlib import Path


def test_pre_pr_sanity_keeps_g3_historical_and_claims_false():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_PRE_PR_SANITY.md").read_text()
    assert "Historical G3 is reconciled as evidence/provenance only" in text
    assert "defaults high-order claims false" in text
