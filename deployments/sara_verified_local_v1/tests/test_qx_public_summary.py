from pathlib import Path


def test_public_summary_keeps_validation_claims_false():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_0_1_PUBLIC_SUMMARY.md").read_text()
    for phrase in ("does not claim physical validation", "external validation", "DARPA qualification", "independent replication"):
        assert phrase in text
