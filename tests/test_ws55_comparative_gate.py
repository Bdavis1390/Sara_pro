import unittest
from tools.ws55_comparative_gate import assess

def fixture():
    return {
        "schema_version": "ws55-v1",
        "baseline_revision": "baseline-a",
        "candidate_revision": "candidate-b",
        "matched_environment": "same host and configuration",
        "matched_workload": "identical synthetic tasks",
        "security_gates": {
            "authorization": True, "receipt_integrity": True,
            "replay_protection": True, "concurrency": True,
            "privacy": True, "critical_regressions_absent": True
        },
        "metrics": {
            "throughput_per_second": {"baseline": 100, "candidate": 160},
            "p95_latency_ms": {"baseline": 100, "candidate": 40},
            "task_completion_seconds": {"baseline": 100, "candidate": 40},
            "operator_error_rate": {"baseline": 0.1, "candidate": 0.04},
            "confirmed_weaknesses": {"baseline": 10, "candidate": 4}
        }
    }

class WS55GateTests(unittest.TestCase):
    def test_passing_fixture_is_internal_only(self):
        result = assess(fixture())
        self.assertTrue(result["all_targets_met"])
        self.assertFalse(result["external_validation"])

    def test_security_gate_missing_fails_closed(self):
        data = fixture()
        del data["security_gates"]["privacy"]
        with self.assertRaises(ValueError):
            assess(data)

    def test_below_target_does_not_pass(self):
        data = fixture()
        data["metrics"]["throughput_per_second"]["candidate"] = 150
        self.assertFalse(assess(data)["all_targets_met"])

    def test_zero_baseline_fails_closed(self):
        data = fixture()
        data["metrics"]["confirmed_weaknesses"]["baseline"] = 0
        with self.assertRaises(ValueError):
            assess(data)

    def test_unmatched_environment_fails_closed(self):
        data = fixture()
        data["matched_environment"] = ""
        with self.assertRaises(ValueError):
            assess(data)

if __name__ == "__main__":
    unittest.main()
