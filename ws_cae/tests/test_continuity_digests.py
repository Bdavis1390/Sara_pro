import unittest

from ws_cae.continuity_digests import digest_set, select_digest, verify_digest_set
from ws_cae.continuity_manifest import ContinuityManifest, EvidenceRef


class ContinuityDigestTests(unittest.TestCase):
    def manifest(self):
        return ContinuityManifest(
            subject_id="urn:example:digital-asset-system",
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

    def test_default_digest_set_has_two_families(self):
        value = digest_set(self.manifest())
        algorithms = tuple(algorithm for algorithm, _ in value.digests)
        self.assertEqual(algorithms, ("sha256", "sha3-256"))
        self.assertTrue(verify_digest_set(self.manifest(), value))

    def test_policy_can_select_preferred_supported_digest(self):
        value = digest_set(self.manifest())
        selected = select_digest(value, ("sha3-256", "sha256"))
        self.assertIsNotNone(selected)
        self.assertEqual(selected[0], "sha3-256")

    def test_unknown_algorithm_fails_closed(self):
        with self.assertRaises(ValueError):
            digest_set(self.manifest(), ("sha256", "future-hash"))

    def test_duplicate_algorithms_are_rejected(self):
        with self.assertRaises(ValueError):
            digest_set(self.manifest(), ("sha256", "sha256"))


if __name__ == "__main__":
    unittest.main()
