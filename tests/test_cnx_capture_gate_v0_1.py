import copy
import json
from pathlib import Path
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
        self.assertEqual([x.gate for x in result.hard_blockers], ["na"])

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
        config["gates"]["na"]["status"] = "VERIFIED"
        result = evaluate(config, "TEAM")
        self.assertTrue(result.development_ready)
        self.assertTrue(result.submission_ready)

    def test_not_applicable_is_blocked_by_default(self):
        result = evaluate(BASE, "TEAM")
        states = {item.gate: item.passing for item in result.hard_gates}
        self.assertFalse(states["na"])

    def test_optional_gate_must_explicitly_opt_into_not_applicable(self):
        config = copy.deepcopy(BASE)
        config["gates"]["na"]["passing_statuses"] = ["VERIFIED", "NOT_APPLICABLE"]
        result = evaluate(config, "TEAM")
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

    def test_schema_is_required_and_exact(self):
        missing = copy.deepcopy(BASE)
        del missing["schema"]
        with self.assertRaises(CaptureGateError):
            validate_config(missing)

        future = copy.deepcopy(BASE)
        future["schema"] = "CNX-CAPTURE-GATE-V0.2"
        with self.assertRaises(CaptureGateError):
            validate_config(future)

    def test_partner_acceptance_can_be_verified_only(self):
        config = copy.deepcopy(BASE)
        config["gates"]["external"]["passing_statuses"] = ["VERIFIED"]
        config["opportunities"]["TEAM"]["hard_gates"] = ["external"]
        config["opportunities"]["TEAM"]["development_gates"] = ["internal"]

        config["gates"]["external"]["status"] = "NOT_APPLICABLE"
        result = evaluate(config, "TEAM")
        self.assertTrue(result.development_ready)
        self.assertFalse(result.submission_ready)

        config["gates"]["external"]["status"] = "VERIFIED"
        config["gates"]["na"]["status"] = "VERIFIED"
        result = evaluate(config, "TEAM")
        self.assertTrue(result.submission_ready)

    def test_missing_gate_collection_is_rejected(self):
        config = copy.deepcopy(BASE)
        del config["opportunities"]["TEAM"]["hard_gates"]
        with self.assertRaises(CaptureGateError):
            validate_config(config)

    def test_empty_hard_gates_rejected(self):
        config = copy.deepcopy(BASE)
        config["opportunities"]["TEAM"]["hard_gates"] = []
        with self.assertRaises(CaptureGateError):
            validate_config(config)

    def test_direct_evaluate_revalidates(self):
        config = copy.deepcopy(BASE)
        del config["opportunities"]["TEAM"]["hard_gates"]
        with self.assertRaises(CaptureGateError):
            evaluate(config, "TEAM")

    def test_malformed_gate_object_rejected(self):
        config = copy.deepcopy(BASE)
        config["gates"]["external"] = []
        with self.assertRaises(CaptureGateError):
            validate_config(config)

    def test_unknown_gate_reference_is_rejected(self):
        config = copy.deepcopy(BASE)
        config["opportunities"]["TEAM"]["hard_gates"].append("missing")
        with self.assertRaises(CaptureGateError):
            validate_config(config)

    def test_real_routes_require_final_approval(self):
        source = Path(__file__).resolve().parents[1] / "config" / "cnx_capture_gates_v0_1.json"
        config = json.loads(source.read_text(encoding="utf-8"))
        validate_config(config)
        for route, final_gate in (
            ("XTECHSEARCH10_SUBMISSION", "xtech_application_final"),
            ("DARPA_INFLUENCE_BENCHMARKS_SUBMISSION", "darpa_application_final"),
        ):
            candidate = copy.deepcopy(config)
            required = set(candidate["opportunities"][route]["hard_gates"])
            required.update(candidate["opportunities"][route]["development_gates"])
            for name in required:
                candidate["gates"][name]["status"] = "VERIFIED"
            candidate["gates"][final_gate]["status"] = "NOT_APPLICABLE"
            result = evaluate(candidate, route)
            self.assertFalse(result.submission_ready)
            self.assertIn(final_gate, [x.gate for x in result.hard_blockers])

    def test_real_legal_entity_cannot_be_na(self):
        source = Path(__file__).resolve().parents[1] / "config" / "cnx_capture_gates_v0_1.json"
        config = json.loads(source.read_text(encoding="utf-8"))
        for name in config["opportunities"]["SCAR_AOI03_DIRECT"]["hard_gates"]:
            config["gates"][name]["status"] = "VERIFIED"
        config["gates"]["capture_package"]["status"] = "VERIFIED"
        config["gates"]["legal_entity"]["status"] = "NOT_APPLICABLE"
        result = evaluate(config, "SCAR_AOI03_DIRECT")
        self.assertFalse(result.submission_ready)

    def test_noncanonical_status_is_rejected(self):
        config = copy.deepcopy(BASE)
        config["gates"]["external"]["status"] = "PROBABLY"
        with self.assertRaises(CaptureGateError):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()