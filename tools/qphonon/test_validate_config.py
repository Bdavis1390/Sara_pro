from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_config import validate, validate_file


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "ws_qphonon_l2_v0_1.json"


class QPhononConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_repository_config_passes(self) -> None:
        self.assertEqual(validate(self.data), [])

    def test_l2_cannot_claim_owned_quantum_hardware(self) -> None:
        data = copy.deepcopy(self.data)
        data["physical_baseline"]["worldshepherd_owned_quantum_hardware"] = True
        errors = validate(data)
        self.assertTrue(any("worldshepherd_owned_quantum_hardware" in error for error in errors))

    def test_holdout_validation_is_mandatory(self) -> None:
        data = copy.deepcopy(self.data)
        data["prime_authorization"]["coherent_transfer_attempt_requires"]["model_holdout_validation_pass"] = False
        errors = validate(data)
        self.assertTrue(any("holdout" in error.lower() for error in errors))

    def test_temperature_hard_screen_is_bounded(self) -> None:
        data = copy.deepcopy(self.data)
        data["parameter_registry"]["device_temperature_k"]["hard_screen_max"] = 0.2
        errors = validate(data)
        self.assertTrue(any("0.125" in error for error in errors))

    def test_l3_requires_independent_reproducibility(self) -> None:
        data = copy.deepcopy(self.data)
        data["promotion_gates"]["L3_CAPABILITY_INTEGRATION"].remove(
            "independent_human_or_partner_can_reproduce_result"
        )
        errors = validate(data)
        self.assertTrue(any("L3 gate" in error for error in errors))

    def test_invalid_json_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            errors = validate_file(path)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
