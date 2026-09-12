import datetime as dt
import unittest

from validate_registry import validate_entry, validate_registry


class RegistryValidationTests(unittest.TestCase):
    def setUp(self):
        self.today = dt.date(2026, 9, 12)
        self.base = {
            "repo": "example/project",
            "number": 42,
            "url": "https://github.com/example/project/issues/42",
            "title": "Example issue",
            "task": "A",
            "priority": "P0",
            "score": 90,
            "upstream_state": "OPEN",
            "collision": "CLEAR",
            "duplicate_checked": True,
            "evidence_maturity": "SOURCE_REVIEWED",
            "claims_state": "NOT CURRENTLY CLAIMED",
            "next_gate": "Reproduce and test.",
            "last_checked": "2026-09-12",
        }

    def test_valid_candidate(self):
        self.assertEqual(validate_entry(dict(self.base), today=self.today), [])

    def test_candidate_with_active_pr_is_rejected(self):
        entry = dict(self.base, collision="ACTIVE_PR")
        errors = validate_entry(entry, today=self.today)
        self.assertTrue(any("P0/P1 candidates must have collision=CLEAR" in error for error in errors))
        self.assertTrue(any("occupied upstream work must be WATCH" in error for error in errors))

    def test_watch_requires_collision_reason(self):
        entry = dict(self.base, priority="WATCH", collision="CLEAR")
        errors = validate_entry(entry, today=self.today)
        self.assertTrue(any("WATCH requires" in error for error in errors))

    def test_closed_requires_closed_upstream(self):
        entry = dict(self.base, priority="CLOSED", upstream_state="OPEN", collision="CLOSED_UPSTREAM")
        errors = validate_entry(entry, today=self.today)
        self.assertTrue(any("CLOSED priority requires upstream_state=CLOSED" in error for error in errors))
        self.assertTrue(any("CLOSED_UPSTREAM collision requires upstream_state=CLOSED" in error for error in errors))

    def test_lab_validation_requires_claim_label(self):
        entry = dict(self.base, evidence_maturity="LAB_VALIDATION", claims_state="HYPOTHESIS")
        errors = validate_entry(entry, today=self.today)
        self.assertTrue(any("REQUIRES LAB VALIDATION" in error for error in errors))

    def test_future_check_date_is_rejected(self):
        entry = dict(self.base, last_checked="2026-09-13")
        errors = validate_entry(entry, today=self.today)
        self.assertTrue(any("cannot be in the future" in error for error in errors))

    def test_duplicate_entries_are_rejected(self):
        doc = {"schema_version": 1, "opportunities": [dict(self.base), dict(self.base)]}
        errors = validate_registry(doc, today=self.today)
        self.assertTrue(any("duplicate registry entry" in error for error in errors))

    def test_duplicate_check_is_mandatory(self):
        entry = dict(self.base, duplicate_checked=False)
        errors = validate_entry(entry, today=self.today)
        self.assertTrue(any("duplicate_checked must be true" in error for error in errors))

    def test_patch_draft_cannot_be_proven_internally_by_declaration(self):
        entry = dict(self.base, evidence_maturity="PATCH_DRAFT", claims_state="PROVEN INTERNALLY")
        errors = validate_entry(entry, today=self.today)
        self.assertTrue(any("patch draft cannot be labeled PROVEN INTERNALLY" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
