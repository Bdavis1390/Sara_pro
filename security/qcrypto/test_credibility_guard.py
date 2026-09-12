import unittest

# Federal dual-track classification is a claims-control state only; it never establishes compliance or approval.
from credibility_guard import EvidenceItem, assess_credibility


class CredibilityGuardTests(unittest.TestCase):
    def test_triangulated_process_requires_external_and_internal_evidence(self):
        evidence = [
            EvidenceItem("Google PRX Quantum", "Google Quantum AI", peer_reviewed=True),
            EvidenceItem("IonQ Walking Cat", "IonQ"),
            EvidenceItem("Luo low-width ECDLP", "Luo et al."),
            EvidenceItem("C4-Helix", "Quantinuum", hardware_demonstrated=True),
            EvidenceItem(
                "QCRYPTO CI",
                "Worldshepherd",
                external=False,
                internal_reproducible=True,
            ),
        ]
        result = assess_credibility(evidence)
        self.assertEqual(result.warrant_state, "TRIANGULATED_CLAIMS_CONTROLLED_IMPLEMENTATION")
        self.assertEqual(result.independent_external_families, 4)
        self.assertTrue(result.peer_reviewed_external_present)
        self.assertTrue(result.hardware_external_present)
        self.assertTrue(result.internal_reproducible_present)
        self.assertFalse(result.standards_authority_present)
        self.assertFalse(result.operational_migration_present)
        self.assertFalse(result.national_security_transition_present)
        self.assertFalse(result.federal_execution_mandate_present)

    def test_multi_axis_record_requires_standards_and_real_migration(self):
        evidence = [
            EvidenceItem("Google PRX Quantum", "Google Quantum AI", peer_reviewed=True),
            EvidenceItem("IonQ Walking Cat", "IonQ"),
            EvidenceItem("Luo low-width ECDLP", "Luo et al."),
            EvidenceItem("C4-Helix", "Quantinuum", hardware_demonstrated=True),
            EvidenceItem("NIST PQC transition", "NIST", standards_authority=True),
            EvidenceItem(
                "Algorand Falcon-1024 mainnet accounts",
                "Algorand Foundation",
                operational_migration_deployment=True,
            ),
            EvidenceItem(
                "QCRYPTO CI",
                "Worldshepherd",
                external=False,
                internal_reproducible=True,
            ),
        ]
        result = assess_credibility(evidence)
        self.assertEqual(result.warrant_state, "MULTI_AXIS_TRIANGULATED_ENGINEERING_RECORD")
        self.assertEqual(result.independent_external_families, 6)
        self.assertTrue(result.standards_authority_present)
        self.assertTrue(result.operational_migration_present)
        self.assertTrue(any("CREDIBILITY WARRANTED FOR PROCESS" in c for c in result.warranted_claims))

    def test_national_security_transition_axis_requires_distinct_official_evidence(self):
        evidence = [
            EvidenceItem("Google PRX Quantum", "Google Quantum AI", peer_reviewed=True),
            EvidenceItem("IonQ Walking Cat", "IonQ"),
            EvidenceItem("C4-Helix", "Quantinuum", hardware_demonstrated=True),
            EvidenceItem("NIST PQC transition", "NIST", standards_authority=True),
            EvidenceItem(
                "Algorand Falcon mainnet",
                "Algorand Foundation",
                operational_migration_deployment=True,
            ),
            EvidenceItem(
                "NSA CSfC CNSA 2.0 transition",
                "NSA CSfC",
                national_security_transition_policy=True,
            ),
            EvidenceItem(
                "QCRYPTO CI",
                "Worldshepherd",
                external=False,
                internal_reproducible=True,
            ),
        ]
        result = assess_credibility(evidence)
        self.assertEqual(result.warrant_state, "NATIONAL_SECURITY_TRANSITION_AWARE_ENGINEERING_RECORD")
        self.assertTrue(result.national_security_transition_present)
        self.assertTrue(any("NATIONAL_SECURITY_TRANSITION_AWARE" in c for c in result.warranted_claims))
        self.assertTrue(any("TRANSITION RELEVANCE" in c for c in result.warranted_claims))

    def test_federal_dual_track_state_requires_civilian_execution_and_nss_policy(self):
        evidence = [
            EvidenceItem("Google PRX Quantum", "Google Quantum AI", peer_reviewed=True),
            EvidenceItem("IonQ Walking Cat", "IonQ"),
            EvidenceItem("C4-Helix", "Quantinuum", hardware_demonstrated=True),
            EvidenceItem("NIST PQC transition", "NIST", standards_authority=True),
            EvidenceItem(
                "Algorand Falcon mainnet",
                "Algorand Foundation",
                operational_migration_deployment=True,
            ),
            EvidenceItem(
                "NSA CSfC CNSA 2.0 transition",
                "NSA CSfC",
                national_security_transition_policy=True,
            ),
            EvidenceItem(
                "EO 14412 and OMB M-26-15 civilian execution",
                "Executive Office of the President / OMB",
                federal_execution_mandate=True,
            ),
            EvidenceItem(
                "QCRYPTO CI",
                "Worldshepherd",
                external=False,
                internal_reproducible=True,
            ),
        ]
        result = assess_credibility(evidence)
        self.assertEqual(result.warrant_state, "FEDERAL_DUAL_TRACK_PQC_TRANSITION_ENGINEERING_RECORD")
        self.assertTrue(result.national_security_transition_present)
        self.assertTrue(result.federal_execution_mandate_present)
        self.assertTrue(any("FEDERAL_EXECUTION_AWARE" in c for c in result.warranted_claims))
        self.assertTrue(any("DUAL-TRACK TRANSITION RELEVANCE" in c for c in result.warranted_claims))

    def test_federal_execution_without_nss_policy_does_not_reach_dual_track_state(self):
        evidence = [
            EvidenceItem("Google PRX Quantum", "Google Quantum AI", peer_reviewed=True),
            EvidenceItem("C4-Helix", "Quantinuum", hardware_demonstrated=True),
            EvidenceItem("NIST PQC transition", "NIST", standards_authority=True),
            EvidenceItem("Algorand Falcon mainnet", "Algorand Foundation", operational_migration_deployment=True),
            EvidenceItem("OMB M-26-15", "Executive Office of the President / OMB", federal_execution_mandate=True),
            EvidenceItem("extra independent source", "Independent family"),
            EvidenceItem("QCRYPTO CI", "Worldshepherd", external=False, internal_reproducible=True),
        ]
        result = assess_credibility(evidence)
        self.assertNotEqual(result.warrant_state, "FEDERAL_DUAL_TRACK_PQC_TRANSITION_ENGINEERING_RECORD")
        self.assertFalse(result.national_security_transition_present)
        self.assertTrue(result.federal_execution_mandate_present)

    def test_external_findings_alone_do_not_warrant_implementation(self):
        result = assess_credibility(
            [
                EvidenceItem("paper a", "family-a", peer_reviewed=True),
                EvidenceItem("paper b", "family-b", hardware_demonstrated=True),
                EvidenceItem("paper c", "family-c"),
            ]
        )
        self.assertEqual(result.warrant_state, "SOURCE_SYNTHESIS_ONLY")
        self.assertFalse(any("IMPLEMENTED_IN_SOFTWARE" in c for c in result.warranted_claims))

    def test_duplicate_source_family_does_not_fake_independence(self):
        result = assess_credibility(
            [
                EvidenceItem("paper a", "same-family", peer_reviewed=True),
                EvidenceItem("paper b", "same-family", hardware_demonstrated=True),
                EvidenceItem("ci", "Worldshepherd", external=False, internal_reproducible=True),
            ]
        )
        self.assertEqual(result.independent_external_families, 1)
        self.assertEqual(result.warrant_state, "INTERNAL_IMPLEMENTATION_ONLY")

    def test_prohibited_overclaims_are_always_explicit(self):
        result = assess_credibility([])
        joined = " ".join(result.excluded_claims)
        self.assertIn("Original authorship", joined)
        self.assertIn("Independent external validation", joined)
        self.assertIn("Government approval", joined)
        self.assertIn("Federal contractor compliance", joined)
        self.assertIn("procurement qualification", joined)
        self.assertIn("production-strength cryptographic key break", joined)
        self.assertIn("cryptographically relevant quantum computer", joined)
        self.assertIn("partial post-quantum deployment", joined)


if __name__ == "__main__":
    unittest.main()
