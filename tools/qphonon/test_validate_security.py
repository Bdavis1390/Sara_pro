from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_security import validate


ROOT = Path(__file__).resolve().parents[2]
PROFILE = json.loads((ROOT / "config" / "ws_qphonon_security_v0_2.json").read_text(encoding="utf-8"))


class SecurityProfileValidatorTests(unittest.TestCase):
    def test_canonical_profile_passes(self) -> None:
        self.assertEqual(validate(PROFILE), [])

    def test_removing_control_fails(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["required_controls"] = data["required_controls"][:-1]
        errors = validate(data)
        self.assertTrue(any("missing hardening controls" in error for error in errors))

    def test_weakening_approval_lifetime_fails(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["approval_lifetime_seconds_max"] = 3600
        self.assertTrue(validate(data))

    def test_allowing_persisted_credentials_fails(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["supply_chain"]["checkout_persist_credentials"] = True
        self.assertTrue(validate(data))


if __name__ == "__main__":
    unittest.main()
