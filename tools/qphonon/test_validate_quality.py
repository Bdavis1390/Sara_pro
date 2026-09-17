from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_quality import validate


ROOT = Path(__file__).resolve().parents[2]
PROFILE = json.loads((ROOT / "config" / "ws_qphonon_quality_v0_2.json").read_text(encoding="utf-8"))


class QualityProfileValidatorTests(unittest.TestCase):
    def test_canonical_profile_passes(self) -> None:
        self.assertEqual(validate(PROFILE), [])

    def test_removing_quality_control_fails(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["required_controls"] = data["required_controls"][:-1]
        errors = validate(data)
        self.assertTrue(any("missing quality controls" in error for error in errors))

    def test_terminal_state_change_fails(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["terminal_states"] = ["COMPLETED"]
        self.assertTrue(validate(data))


if __name__ == "__main__":
    unittest.main()
