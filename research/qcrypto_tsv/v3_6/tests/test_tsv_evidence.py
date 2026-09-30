import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from worldshepherd_qcrypto_kms.tsv.evidence import EvidenceChain
from worldshepherd_qcrypto_kms.tsv.source_evidence import SourceEvidence, validate_source_evidence

T = datetime(2026, 9, 18, 21, 50, tzinfo=timezone.utc)
HASH = "a" * 64


class TestEvidence(unittest.TestCase):
    def test_hash_chain_verifies(self):
        c = EvidenceChain()
        a = c.append("ONE", {"x": 1}, occurred_at=T)
        b = c.append("TWO", {"x": 2}, occurred_at=T + timedelta(seconds=1))
        self.assertTrue(c.verify())
        self.assertEqual(b.previous_hash, a.event_hash)
        self.assertEqual(c.head(), b.event_hash)

    def test_tampered_chain_rejected(self):
        c = EvidenceChain(); e = c.append("ONE", {"x": 1}, occurred_at=T)
        bad = replace(e, event_hash="f" * 64)
        with self.assertRaises(ValueError):
            EvidenceChain([bad])

    def evidence(self, **kw):
        base = dict(symbol="ABC", source_kind="SIP", source_id="cta-utp-sip", observed_at=T - timedelta(seconds=5), effective_at=T - timedelta(seconds=5), payload_sha256=HASH, verified=True)
        base.update(kw)
        return SourceEvidence(**base)

    def test_fresh_verified_source_allows(self):
        r = validate_source_evidence(self.evidence(), expected_symbol="ABC", now=T, max_age_seconds=30, allowed_source_kinds={"SIP"})
        self.assertEqual(r.decision, "ALLOW")

    def test_stale_source_denies(self):
        e = self.evidence(observed_at=T - timedelta(seconds=31))
        self.assertEqual(validate_source_evidence(e, expected_symbol="ABC", now=T, max_age_seconds=30, allowed_source_kinds={"SIP"}).decision, "DENY")

    def test_unverified_source_denies(self):
        e = self.evidence(verified=False)
        self.assertEqual(validate_source_evidence(e, expected_symbol="ABC", now=T, max_age_seconds=30, allowed_source_kinds={"SIP"}).decision, "DENY")

    def test_wrong_symbol_denies(self):
        e = self.evidence(symbol="XYZ")
        self.assertEqual(validate_source_evidence(e, expected_symbol="ABC", now=T, max_age_seconds=30, allowed_source_kinds={"SIP"}).decision, "DENY")

    def test_malformed_hash_denies(self):
        e = self.evidence(payload_sha256="not-a-hash")
        self.assertEqual(validate_source_evidence(e, expected_symbol="ABC", now=T, max_age_seconds=30, allowed_source_kinds={"SIP"}).decision, "DENY")


if __name__ == "__main__":
    unittest.main()

class TestSourceEvidenceParser(unittest.TestCase):
    def test_parse_dict(self):
        from worldshepherd_qcrypto_kms.tsv.source_evidence import source_evidence_from_dict
        e = source_evidence_from_dict({
            "symbol": "ABC",
            "source_kind": "SIP",
            "source_id": "cta-utp-sip",
            "observed_at": "2026-09-18T21:49:55Z",
            "effective_at": "2026-09-18T21:49:55Z",
            "payload_sha256": "c" * 64,
            "verified": True,
        })
        self.assertEqual(e.symbol, "ABC")
        self.assertEqual(e.observed_at.tzinfo, timezone.utc)
