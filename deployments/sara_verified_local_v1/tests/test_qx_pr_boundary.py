from pathlib import Path


def test_pre_pr_mutation_boundary_closed():
    assert "No more files should be added" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_BOUNDARY.md").read_text()
