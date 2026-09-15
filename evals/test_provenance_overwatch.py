#!/usr/bin/env python3
import unittest

from echo_provenance import build_chain, verify_chain
from overwatch_snapshot import build_snapshot


class ProvenanceTests(unittest.TestCase):
    def bundle(self):
        return {
            "system_id": "TEST-SYSTEM",
            "system_version": "v1",
            "evidence": [
                {
                    "evidence_id": "ev-1",
                    "metric_names": ["metric-a"],
                    "source_or_artifact_hash": "sha256:a",
                    "task_hash": "sha256:t",
                    "grader_version": "g1",
                    "claim_state": "PROVEN_INTERNALLY",
                    "evaluation_date": "2026-09-11",
                }
            ],
        }

    def gate(self):
        return {
            "system_id": "TEST-SYSTEM",
            "intelligence_state": "BELOW_AGI",
            "gate_config_schema": "WS-AGI-GATE-V1.4",
            "prime_policy": {
                "deployment_state_input": "BLOCKED",
                "deployment_state_output": "BLOCKED",
                "deployment_state_changed": False,
            },
        }

    def test_generated_chain_verifies(self):
        records = build_chain(self.bundle(), self.gate())
        self.assertEqual(len(records), 2)
        self.assertTrue(verify_chain(records))

    def test_tamper_breaks_verification(self):
        records = build_chain(self.bundle(), self.gate())
        records[1]["payload"]["claim_state"] = "ALTERED"
        self.assertFalse(verify_chain(records))


class OverwatchTests(unittest.TestCase):
    def test_snapshot_surfaces_unknown_and_blocked_metrics(self):
        gate = {
            "system_id": "TEST-SYSTEM",
            "intelligence_state": "BELOW_AGI",
            "candidate_gate": {
                "passed": False,
                "lanes": {
                    "lane-a": {
                        "status": "UNKNOWN",
                        "metrics": [
                            {"metric": "a", "status": "UNKNOWN", "actual": None, "target": 1}
                        ],
                    },
                    "lane-b": {
                        "status": "BLOCKED",
                        "metrics": [
                            {"metric": "b", "status": "BLOCKED", "actual": 2, "target": 3}
                        ],
                    },
                },
            },
            "evidence": {"valid": False, "record_count": 1, "errors": ["missing evidence"]},
            "prime_policy": {
                "deployment_state_input": "BLOCKED",
                "deployment_state_output": "BLOCKED",
                "deployment_state_changed": False,
            },
        }
        snapshot = build_snapshot(gate)
        self.assertIn("REQUIRED_METRIC_UNKNOWN", snapshot["alerts"])
        self.assertIn("INVALIDATED_MEASUREMENT_PRESENT", snapshot["alerts"])
        self.assertEqual(snapshot["deployment_state"], "BLOCKED")
        self.assertEqual(len(snapshot["blockers"]), 2)


if __name__ == "__main__":
    unittest.main()
