from pathlib import Path


def test_next_mutation_is_pr_not_features():
    text = (Path(__file__).parents[1] / "docs" / "WS_QX_LAST_PRE_PR_COMMIT.md").read_text()
    assert "next repository mutation should be pull-request creation" in text
