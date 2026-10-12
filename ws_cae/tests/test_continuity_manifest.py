import unittest

from ws_cae.continuity_manifest import ContinuityManifest, DependencyRef, EvidenceRef, content_id, envelope, validate


class ContinuityManifestTests(unittest.TestCase):
    def sample(self):
        return ContinuityManifest(
            subject_id="urn:example:asset",
            subject_type="ASSET",
            version="1",
            as_of="2026-09-13",
            authority_model="REPLACEABLE_AUTHENTICATOR",
            implementation_maturity="TESTNET",
            protocol_commitment_state="GOVERNANCE_SELECTED",
            pq_authorization_state="PQ_NON_MAINNET",
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
            crypto_agility_state="DOCUMENTED",
            recovery_state="DOCUMENTED",
            dependencies=(DependencyRef("CHAIN_AUTHORITY", "urn:example:chain", True, "PQ_PARTIAL"),),
            evidence=(EvidenceRef("Example", "https://example.com/evidence", "Synthetic evidence."),),
        )

    def test_content_id_is_deterministic(self):
        a = self.sample()
        b = self.sample()
        self.assertEqual(content_id(a), content_id(b))
        self.assertTrue(content_id(a).startswith("sha256:"))

    def test_valid_manifest_has_envelope(self):
        result = envelope(self.sample())
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])

    def test_invalid_evidence_fails_closed(self):
        bad = ContinuityManifest(**{**self.sample().__dict__, "evidence": (EvidenceRef("", "http://example.com", ""),)})
        self.assertTrue(validate(bad))
        self.assertFalse(envelope(bad)["valid"])


if __name__ == "__main__":
    unittest.main()
