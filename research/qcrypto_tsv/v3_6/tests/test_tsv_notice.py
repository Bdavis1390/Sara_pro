import unittest
from copy import deepcopy
from worldshepherd_qcrypto_kms.tsv.notice import NOTICE_SECTIONS, validate_notice


def full_notice():
    n = {key: "not applicable / disclosed" for key in NOTICE_SECTIONS.values()}
    n["disclaimer"] = {
        "not_registered_with_sec": True,
        "sec_has_not_passed_on_merits_or_accuracy": True,
        "not_subject_to_fair_access_requirements": True,
        "denials_not_subject_to_sec_review": True,
        "not_subject_to_regulation_nms": True,
    }
    return n


class TestNotice(unittest.TestCase):
    def test_all_30_sections_present(self):
        self.assertEqual(len(NOTICE_SECTIONS), 30)
        ev = validate_notice(full_notice())
        self.assertEqual(ev.decision, "ALLOW")

    def test_missing_one_section_denies(self):
        n = full_notice(); n.pop("market_data_and_oracles")
        ev = validate_notice(n)
        self.assertEqual(ev.decision, "DENY")
        self.assertTrue(any(f.key == "market_data_and_oracles" and f.status == "FAIL" for f in ev.findings))

    def test_empty_section_denies(self):
        n = full_notice(); n["fees_rebates_discounts_compensation"] = "  "
        self.assertEqual(validate_notice(n).decision, "DENY")

    def test_disclaimer_not_registered_required(self):
        n = full_notice(); n["disclaimer"]["not_registered_with_sec"] = False
        ev = validate_notice(n)
        self.assertEqual(ev.decision, "DENY")

    def test_disclaimer_reg_nms_required(self):
        n = full_notice(); n["disclaimer"]["not_subject_to_regulation_nms"] = False
        self.assertEqual(validate_notice(n).decision, "DENY")


if __name__ == "__main__":
    unittest.main()
