from pathlib import Path


def test_create_pr_against_main():
    assert "Create PR against main" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_EXECUTION_POINT.md").read_text()
