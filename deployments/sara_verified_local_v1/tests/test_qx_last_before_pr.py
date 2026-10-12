from pathlib import Path


def test_no_further_files_before_pr():
    assert "No further files" in (Path(__file__).parents[1] / "docs" / "WS_QX_LAST_BEFORE_PR.md").read_text()
