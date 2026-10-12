from pathlib import Path


def test_scope_freeze_explicitly_excludes_physical_and_program_validation():
    path = Path(__file__).parents[1] / "docs" / "WS_QX_0_1_SCOPE.md"
    text = path.read_text()
    assert "physical/HIL execution" in text
    assert "external blind test execution" in text
    assert "UAS flight test" in text
    assert "program-specific eligibility determination" in text
