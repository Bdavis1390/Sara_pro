import unittest

from ws_cae.continuity_manifest import ContinuityManifest, EvidenceRef, envelope
from ws_cae.continuity_scitt import build_statement


class ContinuityScittIntegrityTests(unittest.TestCase):
    def _envelope(self):
        return envelope(ContinuityManifest(
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
        ))

    def test_tampered_manifest_payload_is_rejected(self):
        env = self._envelope()
        env["manifest"]["recovery_state"] = "TAMPERED"
        with self.assertRaises(ValueError):
            build_statement(env, "did:web:example.invalid", "2026-09-13T22:00:00Z")

    def test_noncanonical_content_id_is_rejected(self):
        env = self._envelope()
        env["content_id"] = env["content_id"].upper().replace("SHA256:", "sha256:")
        with self.assertRaises(ValueError):
            build_statement(env, "did:web:example.invalid", "2026-09-13T22:00:00Z")

    def test_observed_at_requires_timezone(self):
        env = self._envelope()
        with self.assertRaises(ValueError):
            build_statement(env, "did:web:example.invalid", "2026-09-13T22:00:00")


if __name__ == "__main__":
    unittest.main()
