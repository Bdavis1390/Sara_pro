import unittest

from federal_pqc_control_map import MAPPINGS, coverage_summary


class FederalPQCControlMapTests(unittest.TestCase):
    def test_required_worldshepherd_modules_are_present(self):
        summary = coverage_summary()
        self.assertEqual(set(summary["modules"]), {"SARA", "ECHO", "PRIME", "OVERWATCH"})

    def test_core_federal_migration_functions_are_mapped(self):
        ids = {item.requirement_id for item in MAPPINGS}
        expected = {
            "OMB-M26-15-GOV",
            "OMB-M26-15-PLAN",
            "OMB-M26-15-RISK",
            "OMB-M26-15-INVENTORY",
            "OMB-M26-15-AUTOMATION",
            "OMB-M26-15-AGILITY",
            "OMB-M26-15-SUPPLY",
            "OMB-M26-15-REPORT",
        }
        self.assertEqual(ids, expected)

    def test_mapping_does_not_claim_federal_compliance(self):
        summary = coverage_summary()
        self.assertTrue(summary["all_design_only"])
        self.assertEqual(
            summary["claim_boundary"],
            "REQUIREMENT_COVERAGE_MAPPING_NOT_FEDERAL_COMPLIANCE",
        )

    def test_every_mapping_has_evidence_target_and_module_owner(self):
        for item in MAPPINGS:
            self.assertTrue(item.modules)
            self.assertTrue(item.evidence_target.strip())
            self.assertEqual(item.status, "DESIGN_MAPPING")


if __name__ == "__main__":
    unittest.main()
