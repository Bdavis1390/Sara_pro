#!/usr/bin/env python3
import unittest

from build_gate_bundle import merge_adapters


class GateBundleMergeTests(unittest.TestCase):
    def adapter(self, schema, metric_name, metric_value, evidence_id):
        return {
            "schema": schema,
            "system_id": "WS-CANDIDATE",
            "system_version": "v-test",
            "metrics": {metric_name: metric_value},
            "metric_validity": {metric_name: {"valid": True, "reason": "test"}},
            "evidence": [
                {
                    "evidence_id": evidence_id,
                    "metric_names": [metric_name],
                }
            ],
        }

    def test_merges_disjoint_metrics(self):
        a = self.adapter("A", "arc_agi_3_standard_score_pct", 91.0, "ev-a")
        b = self.adapter("B", "metr_80pct_horizon_hours", 9.0, "ev-b")
        bundle = merge_adapters([a, b], "WS-CANDIDATE", "v-test")
        self.assertEqual(bundle["metrics"]["arc_agi_3_standard_score_pct"], 91.0)
        self.assertEqual(bundle["metrics"]["metr_80pct_horizon_hours"], 9.0)
        self.assertEqual(bundle["deployment_state"], "BLOCKED")
        self.assertEqual(bundle["source_adapter_schemas"], ["A", "B"])

    def test_system_identity_mismatch_fails_closed(self):
        a = self.adapter("A", "arc_agi_3_standard_score_pct", 91.0, "ev-a")
        a["system_id"] = "OTHER"
        with self.assertRaises(ValueError):
            merge_adapters([a], "WS-CANDIDATE", "v-test")

    def test_conflicting_metric_values_fail_closed(self):
        a = self.adapter("A", "arc_agi_3_standard_score_pct", 91.0, "ev-a")
        b = self.adapter("B", "arc_agi_3_standard_score_pct", 92.0, "ev-b")
        with self.assertRaises(ValueError):
            merge_adapters([a, b], "WS-CANDIDATE", "v-test")

    def test_duplicate_evidence_ids_fail_closed(self):
        a = self.adapter("A", "arc_agi_3_standard_score_pct", 91.0, "ev-same")
        b = self.adapter("B", "metr_80pct_horizon_hours", 9.0, "ev-same")
        with self.assertRaises(ValueError):
            merge_adapters([a, b], "WS-CANDIDATE", "v-test")


if __name__ == "__main__":
    unittest.main()
