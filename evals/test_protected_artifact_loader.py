#!/usr/bin/env python3
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from evals.protected_artifact_loader import load_protected_tasks


class ProtectedArtifactLoaderTests(unittest.TestCase):
    def make_artifact(self, root, tasks):
        raw = json.dumps({"tasks": tasks}, sort_keys=True).encode("utf-8")
        path = root / "tasks.json"
        path.write_bytes(raw)
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        manifest = {
            "task_count": len(tasks),
            "task_set_hash": digest,
            "artifact_access": {
                "evaluator_controlled": True,
                "public_repo_contains_raw_tasks": False,
                "reference_id": "protected-suite-1",
            },
        }
        return path, manifest

    def test_valid_external_artifact_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, manifest = self.make_artifact(root, [{
                "task_id": "t1",
                "goal": "produce a verifiable result",
                "success_criteria": "completion is independently verifiable",
                "allowed_tools": ["inspect"],
                "max_steps": 4,
            }])
            tasks = load_protected_tasks(manifest, path)
            self.assertEqual(tasks[0].task_id, "t1")
            self.assertEqual(tasks[0].max_steps, 4)

    def test_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, manifest = self.make_artifact(root, [{
                "task_id": "t1", "goal": "g", "success_criteria": "s", "allowed_tools": ["inspect"]
            }])
            manifest["task_set_hash"] = "sha256:" + "0" * 64
            with self.assertRaises(ValueError):
                load_protected_tasks(manifest, path)

    def test_duplicate_ids_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"task_id": "dup", "goal": "g", "success_criteria": "s", "allowed_tools": ["inspect"]}
            path, manifest = self.make_artifact(root, [record, dict(record)])
            with self.assertRaises(ValueError):
                load_protected_tasks(manifest, path)


if __name__ == "__main__":
    unittest.main()
