"""Adversarial regression tests for WorldShepherd structural evidence-gate v0.3."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from claim_gate import audit_package, canonical, digest


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads((ROOT / "examples/preregistration.json").read_text())
        cls.package = json.loads((ROOT / "examples/package.json").read_text())
        cls.pin = digest(canonical(cls.prereg))
        cls.example_root = ROOT / "examples"

    def audit(self, package=None, prereg=None, pin=None, root=None):
        return audit_package(
            copy.deepcopy(self.package if package is None else package),
            copy.deepcopy(self.prereg if prereg is None else prereg),
            self.example_root if root is None else root,
            self.pin if pin is None else pin,
        )

    def has_error(self, report, prefix):
        self.assertTrue(any(e.startswith(prefix) for e in report["errors"]), report["errors"])

    def reconcile(self, p):
        p["summary"]["counts"] = {
            outcome: sum(r.get("outcome") == outcome for r in p["runs"])
            for outcome in ("PASS", "FAIL", "INCONCLUSIVE")
        }
        p["summary"]["run_ids"] = sorted({r["id"] for r in p["runs"] if isinstance(r.get("id"), str)})

    def test_clean_synthetic_envelope(self):
        r = self.audit()
        self.assertEqual(r["integrity"], "PASS")
        self.assertEqual(r["artifacts_verified_sha256"], 3)
        self.assertEqual(r["run_configurations_verified_sha256"], 3)
        self.assertFalse(r["claim_automatically_proven"])
        self.assertTrue(r["requires_human_review"])
        self.assertFalse(r["external_independence_verified"])

    def test_changed_preregistration_rejected(self):
        pre = copy.deepcopy(self.prereg)
        pre["statement"] = "revised without new pin"
        self.has_error(self.audit(prereg=pre), "PREREG_PIN_MISMATCH")

    def test_wrong_pin_rejected(self):
        self.has_error(self.audit(pin="0" * 64), "PREREG_PIN_MISMATCH")

    def test_changed_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(self.example_root / "raw", root / "raw")
            shutil.copytree(self.example_root / "config", root / "config")
            (root / "raw/study.json").write_text("tampered")
            self.has_error(self.audit(root=root), "ARTIFACT_HASH_MISMATCH:run-003")

    def test_wrong_claim_rejected(self):
        p = copy.deepcopy(self.package)
        p["claim_id"] = "unregistered"
        self.has_error(self.audit(package=p), "CLAIM_ID_MISMATCH")

    def test_duplicate_event_rejected(self):
        p = copy.deepcopy(self.package)
        p["runs"][1]["id"] = p["runs"][0]["id"]
        self.reconcile(p)
        self.has_error(self.audit(package=p), "DUPLICATE_OR_INVALID_RUN_ID")

    def test_required_control_missing(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["control"] = "different"
        self.has_error(self.audit(package=p), "REQUIRED_CONTROL_NOT_PASSED:linear_detector")

    def test_failed_control_cannot_be_masked_by_duplicate_pass(self):
        p = copy.deepcopy(self.package)
        r = copy.deepcopy(p["runs"][0])
        r["id"] = "run-004"
        r["outcome"] = "FAIL"
        p["runs"].append(r)
        self.reconcile(p)
        self.has_error(self.audit(package=p), "REQUIRED_CONTROL_HAS_FAILED_RUN:linear_detector")

    def test_failing_control_rejected_even_with_reconciled_summary(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["outcome"] = "FAIL"
        self.reconcile(p)
        self.has_error(self.audit(package=p), "REQUIRED_CONTROL_NOT_PASSED:linear_detector")

    def test_summary_counts_reconciled(self):
        p = copy.deepcopy(self.package)
        p["summary"]["counts"]["PASS"] = 3
        self.has_error(self.audit(package=p), "SUMMARY_EVENT_RECONCILIATION_FAILED")

    def test_summary_event_ids_reconciled(self):
        p = copy.deepcopy(self.package)
        p["summary"]["run_ids"] = ["run-001"]
        self.has_error(self.audit(package=p), "SUMMARY_RUN_ID_RECONCILIATION_FAILED")

    def test_fake_lab_promotion_rejected(self):
        p = copy.deepcopy(self.package)
        p["requested_status"] = "PHYSICAL DATA RECORDED"
        self.has_error(self.audit(package=p), "REQUESTED_STATUS_HAS_NO_VERIFIED_ARTIFACT:lab_measurement")

    def test_false_proof_promotion_rejected(self):
        p = copy.deepcopy(self.package)
        p["requested_status"] = "INDEPENDENTLY PROVEN"
        self.has_error(self.audit(package=p), "UNSUPPORTED_CLAIM_PROMOTION")

    def test_bad_config_digest_rejected(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["config_sha256"] = "gibberish"
        self.has_error(self.audit(package=p), "CONFIG_DIGEST_MISSING")

    def test_traversal_rejected(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["artifact"]["path"] = "../package.json"
        self.has_error(self.audit(package=p), "ARTIFACT_UNAVAILABLE")

    def test_missing_artifact_rejected(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["artifact"]["path"] = "raw/not-here.json"
        self.has_error(self.audit(package=p), "ARTIFACT_UNAVAILABLE")

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(self.example_root / "raw", root / "raw")
            shutil.copytree(self.example_root / "config", root / "config")
            (root / "raw/linear.json").unlink()
            (root / "raw/linear.json").symlink_to(self.example_root / "raw/linear.json")
            self.has_error(self.audit(root=root), "ARTIFACT_UNAVAILABLE")

    def test_duplicate_required_controls_rejected(self):
        pre = copy.deepcopy(self.prereg)
        pre["required_controls"].append("linear_detector")
        self.has_error(self.audit(prereg=pre, pin=digest(canonical(pre))), "DUPLICATE_REQUIRED_CONTROL")

    def test_invalid_run_kind_fails_closed(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["kind"] = ["control"]
        self.has_error(self.audit(package=p), "INVALID_KIND")

    def test_invalid_run_outcome_fails_closed(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["outcome"] = ["PASS"]
        self.has_error(self.audit(package=p), "INVALID_OUTCOME")

    def test_invalid_requested_status_fails_closed(self):
        p = copy.deepcopy(self.package)
        p["requested_status"] = {"test": "PASS"}
        self.has_error(self.audit(package=p), "UNSUPPORTED_CLAIM_PROMOTION")

    def test_anchor_string_not_independent_validation(self):
        p = copy.deepcopy(self.package)
        p["independent_attestation_anchor"] = "sha256:some-unverified-string"
        r = self.audit(package=p)
        self.assertFalse(r["external_independence_verified"])
        self.assertTrue(any("NOT cryptographically verified" in w for w in r["warnings"]))

    def test_config_runtime_custody_not_overclaimed(self):
        r = self.audit()
        self.assertTrue(any("NOT prove those bytes were used" in w for w in r["warnings"]))


    def test_missing_config_artifact_blocks(self):
        p = copy.deepcopy(self.package)
        del p["runs"][0]["config_artifact"]
        r = self.audit(package=p)
        self.has_error(r, "CONFIG_DESCRIPTOR_MALFORMED:run-001")
        self.has_error(r, "REQUIRED_CONTROL_NOT_PASSED:linear_detector")

    def test_config_bytes_modified_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(self.example_root / "raw", root / "raw")
            shutil.copytree(self.example_root / "config", root / "config")
            (root / "config/run_config.json").write_text('{"model":"altered"}\\n')
            r = self.audit(root=root)
            self.has_error(r, "CONFIG_HASH_MISMATCH:run-001")
            self.assertEqual(r["run_configurations_verified_sha256"], 0)

    def test_config_reference_changed_blocks(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["config_artifact"]["sha256"] = "0" * 64
        self.has_error(self.audit(package=p), "CONFIG_HASH_MISMATCH:run-001")

    def test_config_digest_disagreement_blocks(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["config_sha256"] = "1" * 64
        r = self.audit(package=p)
        self.has_error(r, "CONFIG_HASH_MISMATCH:run-001")
        self.has_error(r, "REQUIRED_CONTROL_NOT_PASSED:linear_detector")

    def test_configuration_missing_file_blocks(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["config_artifact"]["path"] = "config/absent.json"
        self.has_error(self.audit(package=p), "CONFIG_UNAVAILABLE:run-001")

    def test_configuration_path_traversal_blocks(self):
        p = copy.deepcopy(self.package)
        p["runs"][0]["config_artifact"]["path"] = "../outside.json"
        self.has_error(self.audit(package=p), "CONFIG_UNAVAILABLE:run-001")

    def test_configuration_symlink_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(self.example_root / "raw", root / "raw")
            shutil.copytree(self.example_root / "config", root / "config")
            (root / "config/run_config.json").unlink()
            (root / "config/run_config.json").symlink_to(self.example_root / "config/run_config.json")
            self.has_error(self.audit(root=root), "CONFIG_UNAVAILABLE:run-001")

    def test_bad_claim_type_fails_closed(self):
        pre = copy.deepcopy(self.prereg)
        pre["claim_type"] = ["physical"]
        self.has_error(self.audit(prereg=pre, pin=digest(canonical(pre))), "UNKNOWN_CLAIM_TYPE")

    def test_inconclusive_simulation_with_bad_config_cannot_qualify_status(self):
        p = copy.deepcopy(self.package)
        p["runs"][2]["config_sha256"] = "0" * 64
        r = self.audit(package=p)
        self.has_error(r, "REQUESTED_STATUS_HAS_NO_VERIFIED_ARTIFACT:simulation")


if __name__ == "__main__":
    unittest.main()
