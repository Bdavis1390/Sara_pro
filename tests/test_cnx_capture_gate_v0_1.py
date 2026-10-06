import copy
import unittest

from tools.capture_gate import CaptureGateError, evaluate, validate_config


BASE = {
    "schema": "CNX-CAPTURE-GATE-V0.1",
    "status_vocabulary": [
        "VERIFIED",
        "IN_PROGRESS",
        "PENDING_EXTERNAL",
        "NOT_STARTED",
        "NOT_APPLICABLE",
    ],
    "gates": {
        "internal": {"status": "VERIFIED", "public_note": "ready"},
        "external": {"status": "PENDING_EXTERNAL", "public_note": "waiting"},
        "na": {"status": "NOT_APPLICABLE", "public_note": "not needed"},
    },
    "opportunities": {
        "TEAM": {
            "route": "teaming",
            "hard_gates": ["internal", "na"],
            "development_gates": ["external"],
            "note": "test",
        }
    },
}


class CaptureGateTests(unittest.TestCase):
    def test_pending_development_gate_blocks_development_and_submission(self):
        result = evaluate(BASE, "TEAM")
        self.assertFalse(result.development_ready)
        self.assertFalse(result.submission_ready)
        self.assertEqual(
            [item.gate for item in result.development_blockers],
            ["external"],
        )
        self.assertEqual(result.hard_blockers, ())

    def test_pending_hard_gate_blocks_submission_not_development(self):
        config = copy.deepcopy(BASE)
        config["opportunities"]["TEAM"]["hard_gates"] = ["external"]
        config["opportunities"]["TEAM"]["development_gates"] = ["internal"]
        result = evaluate(config, "TEAM")
        self.assertTrue(result.development_ready)
        self.assertFalse(result.submission_ready)
        self.assertEqual(
            [item.gate for item in result.hard_blockers],
            ["external"],
        )

    def test_verified_external_gate_opens_route(self):
        config = copy.deepcopy(BASE)
        config["gates"]["external"]["status"] = "VERIFIED"
        result = evaluate(config, "TEAM")
        self.assertTrue(result.development_ready)
        self.assertTrue(result.submission_ready)

    def test_not_applicable_is_passing_by_default(self):
        result = evaluate(BASE, "TEAM")
        states = {item.gate: item.passing for item in result.hard_gates}
        self.assertTrue(states["na"])

    def test_gate_can_require_verified_only(self):
        config = copy.deepcopy(BASE)
        config["gates"]["na"]["passing_statuses"] = ["VERIFIED"]
        result = evaluate(config, "TEAM")
        states = {item.gate: item.passing for item in result.hard_gates}
        self.assertFalse(states["na"])
        self.assertFalse(result.submission_ready)

        config["gates"]["na"]["status"] = "VERIFIED"
        result = evaluate(config, "TEAM")
        states = {item.gate: item.passing for item in result.hard_gates}
        self.assertTrue(states["na"])

    def test_nonpassing_state_cannot_be_configured_as_passing(self):
        config = copy.deepcopy(BASE)
        config["gates"]["external"]["passing_statuses"] = ["NOT_STARTED"]
        with self.assertRaises(CaptureGateError):
            validate_config(config)

    def test_missing_gate_collection_is_rejected(self):
        config = copy.deepcopy(BASE)
        del config["opportunities"]["TEAM"]["hard_gates"]
        with self.assertRaises(CaptureGateError):
            validate_config(config)

    def test_unknown_gate_reference_is_rejected(self):
        config = copy.deepcopy(BASE)
        config["opportunities"]["TEAM"]["hard_gates"].append("missing")
        with self.assertRaises(CaptureGateError):
            validate_config(config)

    def test_noncanonical_status_is_rejected(self):
        config = copy.deepcopy(BASE)
        config["gates"]["external"]["status"] = "PROBABLY"
        with self.assertRaises(CaptureGateError):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
