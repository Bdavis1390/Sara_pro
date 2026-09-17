from __future__ import annotations

import json
import unittest
from pathlib import Path

from drift_state import evaluate


ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config" / "ws_qphonon_l2_v0_1.json").read_text(encoding="utf-8"))

ENVELOPE = {
    "detuning": {"min": -500000.0, "max": 500000.0},
    "device_temperature": {"min": 0.0, "max": 0.125},
    "t2": {"min": 2.0e-6},
    "acoustic_drive_efficiency": {"min": 0.80, "max": 1.20},
    "g1": {"min": 2.0e6, "max": 4.0e6},
    "g2": {"min": 2.0e6, "max": 4.0e6},
    "kappa_m": {"min": 0.0, "max": 1.0e6},
    "transducer_response": {"min": 0.80, "max": 1.20},
    "orbital_leakage_model": {"min": 0.0, "max": 1.0e-3},
}

NOMINAL = {
    "detuning": 1.0e5,
    "device_temperature": 0.100,
    "t2": 5.0e-6,
    "acoustic_drive_efficiency": 1.0,
    "g1": 3.0e6,
    "g2": 2.9e6,
    "kappa_m": 3.5e5,
    "transducer_response": 0.98,
    "orbital_leakage_model": 5.0e-4,
}


class DriftStateTests(unittest.TestCase):
    def test_nominal_state_is_within_envelope(self) -> None:
        decision = evaluate(CONFIG, NOMINAL, ENVELOPE)
        self.assertTrue(decision.within_envelope)
        self.assertEqual(decision.disposition, "WITHIN_ENVELOPE")
        self.assertEqual(decision.violations, [])
        self.assertEqual(decision.missing, [])

    def test_temperature_drift_forces_characterize(self) -> None:
        snapshot = dict(NOMINAL)
        snapshot["device_temperature"] = 0.140
        decision = evaluate(CONFIG, snapshot, ENVELOPE)
        self.assertFalse(decision.within_envelope)
        self.assertEqual(decision.disposition, "CHARACTERIZE")
        self.assertIn("device_temperature:ABOVE_MAX", decision.violations)

    def test_missing_measurement_forces_characterize(self) -> None:
        snapshot = dict(NOMINAL)
        del snapshot["detuning"]
        decision = evaluate(CONFIG, snapshot, ENVELOPE)
        self.assertFalse(decision.within_envelope)
        self.assertEqual(decision.disposition, "CHARACTERIZE")
        self.assertIn("detuning", decision.missing)

    def test_untracked_envelope_field_is_rejected(self) -> None:
        envelope = dict(ENVELOPE)
        envelope["invented_parameter"] = {"min": 0.0, "max": 1.0}
        decision = evaluate(CONFIG, NOMINAL, envelope)
        self.assertFalse(decision.within_envelope)
        self.assertEqual(decision.disposition, "CHARACTERIZE")
        self.assertIn("invented_parameter:UNTRACKED_ENVELOPE_FIELD", decision.violations)


if __name__ == "__main__":
    unittest.main()
