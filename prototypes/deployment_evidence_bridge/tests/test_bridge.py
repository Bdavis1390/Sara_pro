"""Reference implementation tests. No network access or external runtime required."""
import csv
import io
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bridge import build, csv_safe, normalize, relative_file, digest

EX = ROOT / "examples"
NOW = "2026-10-06T19:00:00Z"


class TestEvidenceBridge(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((EX / "deployments.json").read_text(encoding="utf-8"))

    def results(self):
        return normalize(EX, self.doc, NOW)

    def test_alignment_is_not_attestation(self):
        result, rows = self.results()
        one, two = result["deployments"]
        self.assertEqual(one["reported_observation"]["alignment"], "MATCH_REPORTED")
        self.assertFalse(one["reported_observation"]["independently_verified"])
        self.assertEqual(two["reported_observation"]["alignment"], "UNVERIFIED")
        self.assertEqual(two["reported_observation"]["freshness"], "NOT_OBSERVED")
        self.assertEqual(one["regulatory_status"], "NO_COMPLIANCE_DETERMINATION")
        self.assertEqual(one["vulnerability_status"], "SOURCE_PROVIDED_UNVALIDATED")
        self.assertEqual(one["finding_count"], 0)
        self.assertEqual(len(rows), 4)

    def test_drift_reported(self):
        self.doc["deployments"][0]["observed_image_digest"] = "sha256:" + "c" * 64
        result, _ = self.results()
        self.assertEqual(result["deployments"][0]["reported_observation"]["alignment"], "DRIFT_REPORTED")

    def test_stale_observation_never_promoted(self):
        self.doc["deployments"][0]["observed_at"] = "2026-10-01T19:00:00Z"
        result, _ = self.results()
        observed = result["deployments"][0]["reported_observation"]
        self.assertEqual(observed["freshness"], "STALE_REPORTED")
        self.assertEqual(observed["alignment"], "MATCH_REPORTED")
        self.assertIn("fresh_runtime_report", result["deployments"][0]["evidence_gap"])

    def test_future_observation_rejected(self):
        self.doc["deployments"][0]["observed_at"] = "2026-10-06T19:06:00Z"
        with self.assertRaisesRegex(ValueError, "future"):
            self.results()

    def test_missing_observation_source_rejected(self):
        del self.doc["deployments"][0]["observation_source"]
        with self.assertRaisesRegex(ValueError, "observation_source"):
            self.results()

    def test_orphaned_observation_metadata_rejected(self):
        self.doc["deployments"][1]["observation_source"] = "invented"
        with self.assertRaisesRegex(ValueError, "without observed_image_digest"):
            self.results()

    def test_timezone_required(self):
        self.doc["deployments"][0]["observed_at"] = "2026-10-06T18:00:00"
        with self.assertRaisesRegex(ValueError, "Timezone"):
            self.results()

    def test_duplicate_deployment_rejected(self):
        self.doc["deployments"].append(deepcopy(self.doc["deployments"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.results()

    def test_non_dictionary_deployment_rejected(self):
        self.doc["deployments"].append(None)
        with self.assertRaisesRegex(ValueError, "must be objects"):
            self.results()

    def test_duplicate_key_delimiter_cannot_collide(self):
        doc = deepcopy(self.doc)
        doc["deployments"][0]["application"] = "a|b"
        doc["deployments"][0]["environment"] = "c"
        first = self.results()[0]["deployments"][0]["record_id"]
        second = normalize(EX, doc, NOW)[0]["deployments"][0]["record_id"]
        self.assertNotEqual(first, second)

    def test_invalid_digest_rejected(self):
        self.doc["deployments"][0]["desired_image_digest"] = "sha256:ABC"
        with self.assertRaisesRegex(ValueError, "desired_image_digest"):
            self.results()

    def test_canonical_url_disallows_credentials(self):
        self.doc["deployments"][0]["canonical_project_url"] = "https://someone:secret@example.org/project"
        with self.assertRaisesRegex(ValueError, "without credentials"):
            self.results()

    def test_canonical_url_disallows_fragment(self):
        self.doc["deployments"][0]["canonical_project_url"] = "https://example.org/project#token"
        with self.assertRaisesRegex(ValueError, "fragment"):
            self.results()

    def test_csv_formula_escaped(self):
        for value in ("=HYPERLINK(\"https://example.org\")", "+SUM(1,2)", "-42", "@cmd", "  =1+1", "\t=1+1"):
            self.assertTrue(csv_safe(value).startswith("'"))
        self.assertEqual(csv_safe("safe-app"), "safe-app")

    def test_csv_export_escapes_attacker_controlled_application(self):
        self.doc["deployments"][0]["application"] = "=1+1"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "manifest.json"
            p.write_text(json.dumps(self.doc))
            # Paths used in manifest are relative to input directory.
            (Path(d) / "sbom.json").write_bytes((EX / "sbom.json").read_bytes())
            (Path(d) / "findings.json").write_bytes((EX / "findings.json").read_bytes())
            build(p, Path(d) / "out", now=NOW)
            with (Path(d) / "out" / "inventory_evidence.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["application"], "'=1+1")

    def test_symlink_and_traversal_blocked(self):
        with self.assertRaisesRegex(ValueError, "inside input directory"):
            relative_file(EX, "../../etc/passwd")
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / "outside"
            link.symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "inside input directory"):
                relative_file(Path(d), "outside")

    def test_invalid_components_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "sbom.json").write_text(json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6", "components": "bad"}))
            (root / "findings.json").write_bytes((EX / "findings.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "CycloneDX"):
                normalize(root, self.doc, NOW)

    def test_source_digest_preserved_but_unverified(self):
        result, _ = self.results()
        self.assertIn("sbom.json", result["source_digests"])
        self.assertEqual(result["source_digests"]["sbom.json"], digest((EX / "sbom.json").read_bytes()))
        self.assertFalse(result["deployments"][0]["reported_observation"]["independently_verified"])

    def test_no_raw_findings_copied_into_report(self):
        result, _ = self.results()
        self.assertIn("finding_count", result["deployments"][0])
        self.assertNotIn("vulnerability_findings", result["deployments"][0])

    def test_limit_deployments(self):
        self.doc["deployments"] = [{}] * 1001
        with self.assertRaisesRegex(ValueError, "1000"):
            self.results()

    def test_control_characters_blocked(self):
        self.doc["deployments"][0]["application"] = "bad\napp"
        with self.assertRaisesRegex(ValueError, "Control"):
            self.results()

    def test_export(self):
        with tempfile.TemporaryDirectory() as d:
            build(EX / "deployments.json", Path(d), now=NOW)
            self.assertTrue((Path(d) / "inventory_evidence.csv").is_file())
            report = json.loads((Path(d) / "deployment_evidence.json").read_text())
            self.assertEqual(len(report["deployments"]), 2)
            self.assertEqual(report["schema"], "ws-deployment-evidence-bridge-poc-v0.2")
            self.assertIn("deployments.json", report["source_digests"])


if __name__ == "__main__":
    unittest.main()
