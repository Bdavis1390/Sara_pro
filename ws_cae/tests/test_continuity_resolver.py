import unittest

from ws_cae.continuity_manifest import ContinuityManifest, EvidenceRef, envelope
from ws_cae.continuity_resolver import resolve
from ws_cae.continuity_transition import from_envelopes


def state(subject: str, auth: str):
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


class ContinuityResolverTests(unittest.TestCase):
    def test_linear_migration_resolves_to_latest_state(self):
        subject = "urn:example:asset"
        a, b, c = state(subject, "AUTH_V1"), state(subject, "AUTH_V2"), state(subject, "AUTH_V3")
        t1 = from_envelopes(a, b, reason="AUTHORITY_ROTATION", effective_at="2026-09-13T23:00:00Z")
        t2 = from_envelopes(b, c, reason="ALGORITHM_MIGRATION", effective_at="2026-09-13T23:10:00Z")
        manifests = {item["content_id"]: item for item in (a, b, c)}
        result = resolve(subject_id=subject, genesis_content_id=a["content_id"], transitions=(t1, t2), manifests_by_content_id=manifests)
        self.assertTrue(result.resolved)
        self.assertEqual(result.current_content_id, c["content_id"])

    def test_fork_fails_closed(self):
        subject = "urn:example:asset"
        a, b, c = state(subject, "AUTH_V1"), state(subject, "AUTH_V2"), state(subject, "AUTH_ALT")
        t1 = from_envelopes(a, b, reason="AUTHORITY_ROTATION", effective_at="2026-09-13T23:00:00Z")
        t2 = from_envelopes(a, c, reason="AUTHORITY_ROTATION", effective_at="2026-09-13T23:01:00Z")
        manifests = {item["content_id"]: item for item in (a, b, c)}
        result = resolve(subject_id=subject, genesis_content_id=a["content_id"], transitions=(t1, t2), manifests_by_content_id=manifests)
        self.assertFalse(result.resolved)
        self.assertTrue(any("fork" in issue for issue in result.issues))

    def test_missing_tip_manifest_fails_closed(self):
        subject = "urn:example:asset"
        a, b = state(subject, "AUTH_V1"), state(subject, "AUTH_V2")
        t1 = from_envelopes(a, b, reason="AUTHORITY_ROTATION", effective_at="2026-09-13T23:00:00Z")
        result = resolve(subject_id=subject, genesis_content_id=a["content_id"], transitions=(t1,), manifests_by_content_id={a["content_id"]: a})
        self.assertFalse(result.resolved)
        self.assertTrue(any("unavailable" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
