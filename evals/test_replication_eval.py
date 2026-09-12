#!/usr/bin/env python3
import json
import unittest
from pathlib import Path

from adapters.replication_eval import normalize

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "ws_replication_eval_v1.json").read_text(encoding="utf-8"))


class ReplicationAdapterTests(unittest.TestCase):
    def source(self, level="candidate"):
        count = CONFIG[level]["min_independent_replications"]
        state = "AGI_VERIFIED" if level == "verified" else "AGI_CANDIDATE"
        return {
            "system_id": "TEST-SYSTEM",
            "system_version": "v1",
            "evaluation_date": "2026-09-11",
            "environment": "protected replication aggregation",
            "target_level": level,
            "task_hash": "sha256:replication-suite",
            "grader_version": "replication-test-v1",
            "source_or_artifact_hash": "sha256:replication-records",
            "replications": [
                {
                    "replication_id": f"rep-{i}",
                    "evaluator_org": f"org-{i}",
                    "infrastructure_id": f"infra-{i}",
                    "result_state": state,
                    "controls": dict(CONFIG["required_controls"]),
                    "unresolved_integrity_failures": 0,
                    "artifact_hash": f"sha256:artifact-{i}",
                }
                for i in range(count)
            ],
        }

    def test_candidate_counts_distinct_replications(self):
        output = normalize(self.source("candidate"), CONFIG)
        self.assertEqual(output["metrics"]["independent_replications"], 2)
        self.assertEqual(output["metrics"]["unresolved_evidence_integrity_failures"], 0)
        self.assertTrue(all(item["valid"] for item in output["metric_validity"].values()))

    def test_verified_requires_verified_state(self):
        source = self.source("verified")
        source["replications"][0]["result_state"] = "AGI_CANDIDATE"
        output = normalize(source, CONFIG)
        self.assertEqual(output["metrics"]["independent_replications"], 2)

    def test_duplicate_independence_key_is_invalid(self):
        source = self.source("candidate")
        source["replications"][1]["evaluator_org"] = source["replications"][0]["evaluator_org"]
        source["replications"][1]["infrastructure_id"] = source["replications"][0]["infrastructure_id"]
        output = normalize(source, CONFIG)
        self.assertFalse(output["metric_validity"]["independent_replications"]["valid"])
        self.assertTrue(output["record_errors"])

    def test_integrity_failures_are_counted(self):
        source = self.source("candidate")
        source["replications"][0]["unresolved_integrity_failures"] = 1
        output = normalize(source, CONFIG)
        self.assertEqual(output["metrics"]["unresolved_evidence_integrity_failures"], 1)


if __name__ == "__main__":
    unittest.main()
