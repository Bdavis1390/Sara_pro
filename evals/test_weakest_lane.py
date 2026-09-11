#!/usr/bin/env python3
import unittest

from weakest_lane import rank_lanes


class WeakestLaneTests(unittest.TestCase):
    def evaluation(self):
        return {
            "system_id": "WS-TEST",
            "intelligence_state": "BELOW_AGI",
            "candidate_gate": {
                "lanes": {
                    "novel_generalization": {
                        "status": "FAIL",
                        "metrics": [
                            {"metric": "arc", "status": "FAIL", "actual": 60.0, "target": 90.0}
                        ],
                    },
                    "long_horizon_autonomy": {
                        "status": "BLOCKED",
                        "metrics": [
                            {"metric": "horizon", "status": "BLOCKED", "actual": 20.0, "target": 40.0}
                        ],
                    },
                    "economic_breadth": {
                        "status": "UNKNOWN",
                        "metrics": [
                            {"metric": "economic", "status": "UNKNOWN", "actual": None, "target": 90.0}
                        ],
                    },
                    "tool_workflow_reliability": {
                        "status": "PASS",
                        "metrics": [
                            {"metric": "workflow", "status": "PASS", "actual": 96.0, "target": 95.0}
                        ],
                    },
                }
            },
        }

    def test_blocked_measurement_is_prioritized_before_unknown_and_fail(self):
        result = rank_lanes(self.evaluation())
        self.assertEqual(result["top_priority"]["lane"], "long_horizon_autonomy")
        statuses = [row["status"] for row in result["ranked_nonpassing_lanes"]]
        self.assertEqual(statuses, ["BLOCKED", "UNKNOWN", "FAIL"])

    def test_passed_lane_is_not_actionable(self):
        result = rank_lanes(self.evaluation())
        lanes = {row["lane"] for row in result["ranked_nonpassing_lanes"]}
        self.assertNotIn("tool_workflow_reliability", lanes)

    def test_verified_gate_is_required_when_requested(self):
        with self.assertRaises(ValueError):
            rank_lanes(self.evaluation(), "verified")


if __name__ == "__main__":
    unittest.main()
