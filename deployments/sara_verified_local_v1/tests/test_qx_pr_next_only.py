from pathlib import Path


def test_no_additional_rc1_content_before_pr():
    assert "No additional RC1 content before PR" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_NEXT_ONLY.md").read_text()
