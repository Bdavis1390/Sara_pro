from pathlib import Path


def test_open_pr_marker_targets_protected_main():
    assert "protected main" in (Path(__file__).parents[1] / "docs" / "WS_QX_OPEN_PR.md").read_text()
