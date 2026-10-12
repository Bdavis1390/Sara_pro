import unittest

from ws_cae.continuity_manifest import ContinuityManifest, EvidenceRef, envelope
from ws_cae.continuity_scitt import build_statement


class ContinuityScittTests(unittest.TestCase):
    def _envelope(self):
        manifest = ContinuityManifest(
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
            dependencies=tuple(),
            evidence=(EvidenceRef("Example", "https://example.com/evidence", "Synthetic evidence."),),
        )
        return envelope(manifest)

    def test_statement_preserves_content_id(self):
        env = self._envelope()
        statement = build_statement(env, "did:web:example.invalid", "2026-09-13T22:00:00Z")
        self.assertEqual(statement["subject"]["content_id"], env["content_id"])
        self.assertEqual(statement["subject"]["id"], "urn:example:asset")

    def test_invalid_manifest_rejected(self):
        env = self._envelope()
        env["valid"] = False
        with self.assertRaises(ValueError):
            build_statement(env, "did:web:example.invalid")


if __name__ == "__main__":
    unittest.main()
