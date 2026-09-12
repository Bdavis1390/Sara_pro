import unittest

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
        self.assertIn("production-strength cryptographic key break", joined)
        self.assertIn("cryptographically relevant quantum computer", joined)


if __name__ == "__main__":
    unittest.main()
