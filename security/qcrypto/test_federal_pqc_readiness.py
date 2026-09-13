import unittest

from federal_pqc_readiness import ControlEvidence, assess_control


class FederalPQCReadinessTests(unittest.TestCase):
    def test_mapping_alone_stays_design_only(self):
        result = assess_control(ControlEvidence("OMB-M26-15-INVENTORY", mapped=True))
        self.assertEqual(result.state, "DESIGN_MAPPING")
        self.assertEqual(result.excluded_claim, "FEDERAL_COMPLIANCE_NOT_ESTABLISHED")

    def test_implementation_requires_mapping(self):
        result = assess_control(
            ControlEvidence("OMB-M26-15-AUTOMATION", implementation_artifact=True)
        )
        self.assertEqual(result.state, "INVALID_EVIDENCE_SEQUENCE")

    def test_internal_proof_requires_mapping_and_implementation(self):
        result = assess_control(
            ControlEvidence(
                "OMB-M26-15-REPORT",
                mapped=True,
                implementation_artifact=True,
                internal_test_passed=True,
            )
        )
        self.assertEqual(result.state, "PROVEN_INTERNALLY")
        self.assertEqual(result.excluded_claim, "FEDERAL_COMPLIANCE_NOT_ESTABLISHED")

    def test_independent_reproduction_requires_complete_prior_chain(self):
        bad = assess_control(
            ControlEvidence(
                "OMB-M26-15-GOV",
                mapped=True,
                independent_review_recorded=True,
            )
        )
        self.assertEqual(bad.state, "INVALID_EVIDENCE_SEQUENCE")

        good = assess_control(
            ControlEvidence(
                "OMB-M26-15-GOV",
                mapped=True,
                implementation_artifact=True,
                internal_test_passed=True,
                independent_review_recorded=True,
            )
        )
        self.assertEqual(good.state, "INDEPENDENTLY_REPRODUCED")
        self.assertEqual(good.excluded_claim, "FEDERAL_COMPLIANCE_NOT_ESTABLISHED")


if __name__ == "__main__":
    unittest.main()
