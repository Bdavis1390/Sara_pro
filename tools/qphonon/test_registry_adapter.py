import json
import unittest
from pathlib import Path

from registry_adapter import REQUIRED_PARAMETER_KEYS, build_record


class RegistryAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(
            (Path(__file__).resolve().parents[2] / "config" / "ws_qphonon_l2_v0_1.json").read_text(encoding="utf-8")
        )

    def test_complete_record_preserves_claims_state(self):
        parameters = {key: 1.0 for key in REQUIRED_PARAMETER_KEYS}
        record = build_record(self.config, parameters, {"source": "synthetic_test"})
        self.assertTrue(record.complete)
        self.assertEqual(record.missing_parameters, [])
        self.assertEqual(record.claims_state, "ARCHITECTURE_INTEGRATED_PHYSICAL_CAPABILITY_NOT_CLAIMED")

    def test_missing_parameters_are_not_invented(self):
        record = build_record(self.config, {"g1_hz": 1.0}, {"source": "synthetic_test"})
        self.assertFalse(record.complete)
        self.assertIn("g2_hz", record.missing_parameters)
        self.assertNotIn("g2_hz", record.parameters)

    def test_unknown_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            build_record(self.config, {"invented_parameter": 1.0}, {})


if __name__ == "__main__":
    unittest.main()
