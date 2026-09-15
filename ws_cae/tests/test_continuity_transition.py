import unittest

from ws_cae.continuity_manifest import ContinuityManifest, EvidenceRef, envelope
from ws_cae.continuity_transition import from_envelopes, transition_id


def manifest(subject: str, auth: str):
    return envelope(ContinuityManifest(
        subject_id=subject,
        subject_type="ASSET",
        version="1",
        as_of="2026-09-13",
        authority_model=auth,
        implementation_maturity="MAINNET",
        protocol_commitment_state="MAINNET",
        pq_authorization_state="PQ_MAINNET",
        consensus_pq_state="CLASSICAL_OR_UNPROVEN",
        crypto_agility_state="DOCUMENTED",
        recovery_state="DOCUMENTED",
        dependencies=tuple(),
        evidence=(EvidenceRef("Example", "https://example.com/evidence", "Synthetic evidence."),),
    ))


class ContinuityTransitionTests(unittest.TestCase):
    def test_same_subject_transition_is_content_addressed(self):
        old = manifest("urn:example:asset", "AUTH_V1")
        new = manifest("urn:example:asset", "AUTH_V2")
        transition = from_envelopes(old, new, reason="AUTHORITY_ROTATION", effective_at="2026-09-13T23:00:00Z")
        self.assertEqual(transition.previous_content_id, old["content_id"])
        self.assertEqual(transition.new_content_id, new["content_id"])
        self.assertTrue(transition_id(transition).startswith("sha256:"))
        self.assertEqual(transition_id(transition), transition_id(transition))

    def test_cross_subject_transition_is_rejected(self):
        old = manifest("urn:example:a", "AUTH_V1")
        new = manifest("urn:example:b", "AUTH_V2")
        with self.assertRaises(ValueError):
            from_envelopes(old, new, reason="AUTHORITY_ROTATION", effective_at="2026-09-13T23:00:00Z")

    def test_noop_transition_is_rejected(self):
        old = manifest("urn:example:asset", "AUTH_V1")
        with self.assertRaises(ValueError):
            from_envelopes(old, old, reason="EVIDENCE_UPDATE", effective_at="2026-09-13T23:00:00Z")


if __name__ == "__main__":
    unittest.main()
