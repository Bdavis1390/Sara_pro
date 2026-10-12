from pathlib import Path


def test_final_instruction_proceeds():
    assert "Proceed" in (Path(__file__).parents[1] / "docs" / "WS_QX_PR_CREATE_FINAL.md").read_text()
