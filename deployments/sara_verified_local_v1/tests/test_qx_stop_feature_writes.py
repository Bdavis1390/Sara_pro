from pathlib import Path


def test_only_planned_next_mutation_is_pr():
    assert "only planned next mutation" in (Path(__file__).parents[1] / "docs" / "WS_QX_STOP_FEATURE_WRITES.md").read_text()
