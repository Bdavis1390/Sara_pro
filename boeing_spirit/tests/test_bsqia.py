import json
import unittest
from pathlib import Path

from boeing_spirit.adversarial_campaign import generate_campaign, run_campaign
from boeing_spirit.contact_gate import TARGET, evaluate as evaluate_contact, zero_failure_exact_lower_bound
from boeing_spirit.quality_assurance import BLOCK, PASS, evaluate_corpus, evaluate_record


ROOT = Path(__file__).resolve().parents[2]


class QualityAssuranceTests(unittest.TestCase):
    def setUp(self):
        fixture = json.loads((ROOT / "boeing_spirit/fixtures/synthetic_supplier_records.v1.json").read_text())
        self.records = fixture["records"]
        self.clean = next(r for r in self.records if r["record_id"] == "CLEAN-001")

    def test_synthetic_fixture_is_exactly_classified(self):
        report = evaluate_corpus(self.records)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["confusion"], {"tp_block": 10, "tn_pass": 2, "fp_block": 0, "fn_pass": 0})
        self.assertEqual(report["critical_false_negative_count"], 0)
        self.assertIsNone(report["external_solution_probability_pct"])
        self.assertEqual(report["contact_decision"], "NO_CONTACT")

    def test_each_expected_disposition_matches(self):
        for record in self.records:
            with self.subTest(record=record["record_id"]):
                result = evaluate_record(record)
                self.assertEqual(result["disposition"], record["expected_disposition"])

    def test_schedule_override_fails_closed(self):
        record = next(r for r in self.records if r["record_id"] == "OVERRIDE-FAIL")
        result = evaluate_record(record)
        self.assertEqual(result["disposition"], BLOCK)
        self.assertIn("SCHEDULE_OVERRIDE_REQUIRES_SEPARATE_AUTHORITY", {f["code"] for f in result["findings"]})

    def test_clean_record_passes(self):
        self.assertEqual(evaluate_record(self.clean)["disposition"], PASS)

    def test_adversarial_campaign_has_all_256_boolean_combinations(self):
        cases = generate_campaign(self.clean)
        self.assertEqual(len(cases), 256)
        self.assertEqual(sum(1 for case in cases if case["expected"] == PASS), 1)
        self.assertEqual(sum(1 for case in cases if case["expected"] == BLOCK), 255)

    def test_adversarial_campaign_fails_closed_without_misses(self):
        report = run_campaign(self.clean)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["case_count"], 256)
        self.assertEqual(report["blocked_count"], 255)
        self.assertEqual(report["pass_count"], 1)
        self.assertEqual(report["mismatch_count"], 0)
        self.assertEqual(report["critical_false_negative_count"], 0)
        self.assertEqual(report["contact_decision"], "NO_CONTACT")


class ContactGateTests(unittest.TestCase):
    def test_228_zero_failure_trials_do_not_reach_threshold(self):
        self.assertLess(zero_failure_exact_lower_bound(228, 228), TARGET)

    def test_229_zero_failure_trials_reach_threshold(self):
        self.assertGreaterEqual(zero_failure_exact_lower_bound(229, 229), TARGET)

    def test_any_failure_does_not_satisfy_current_zero_failure_policy(self):
        self.assertEqual(zero_failure_exact_lower_bound(228, 229), 0.0)

    def test_current_synthetic_evidence_cannot_authorize_contact(self):
        evidence = json.loads((ROOT / "boeing_spirit/evidence/current_contact_evidence.v1.json").read_text())
        report = evaluate_contact(evidence)
        self.assertEqual(report["decision"], "NO_CONTACT")
        self.assertIn("external_independent_evidence", report["failed_gates"])
        self.assertIn("statistical_lower_bound_98_7", report["failed_gates"])
        self.assertIn("independent_review", report["failed_gates"])
        self.assertIn("human_acceptance", report["failed_gates"])


if __name__ == "__main__":
    unittest.main()
