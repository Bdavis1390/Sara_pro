import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from worldshepherd_qcrypto_kms.tsv.evidence import EvidenceChain
from worldshepherd_qcrypto_kms.tsv.notice import NOTICE_SECTIONS
from worldshepherd_qcrypto_kms.tsv.runtime import authorize_bundle
from worldshepherd_qcrypto_kms.tsv.source_evidence import SourceEvidence
from tests.test_tsv_policy import BASE

T = datetime(2026, 9, 18, 21, 50, tzinfo=timezone.utc)


def full_notice():
    n = {key: "disclosed" for key in NOTICE_SECTIONS.values()}
    n["disclaimer"] = {
        "not_registered_with_sec": True,
        "sec_has_not_passed_on_merits_or_accuracy": True,
        "not_subject_to_fair_access_requirements": True,
        "denials_not_subject_to_sec_review": True,
        "not_subject_to_regulation_nms": True,
    }
    return n


def evidence(age_seconds=5):
    return SourceEvidence(
        symbol="ABC",
        source_kind="SIP",
        source_id="cta-utp-sip",
        observed_at=T - timedelta(seconds=age_seconds),
        effective_at=T - timedelta(seconds=age_seconds),
        payload_sha256="b" * 64,
        verified=True,
    )


class TestRuntime(unittest.TestCase):
    def test_bundle_allows_when_all_gates_allow(self):
        c = EvidenceChain()
        r = authorize_bundle(BASE, full_notice(), now=T, symbol="ABC", market_evidence=evidence(), require_market_evidence=True, chain=c)
        self.assertEqual(r.decision, "ALLOW")
        self.assertTrue(c.verify())
        self.assertEqual(r.evidence_head, c.head())

    def test_notice_failure_denies_bundle(self):
        n = full_notice(); n.pop("systems_safeguards")
        self.assertEqual(authorize_bundle(BASE, n, now=T).decision, "DENY")

    def test_policy_failure_denies_bundle(self):
        s = deepcopy(BASE); s["public_permissionless_ledger"] = False
        self.assertEqual(authorize_bundle(s, full_notice(), now=T).decision, "DENY")

    def test_required_stale_market_evidence_denies_bundle(self):
        r = authorize_bundle(BASE, full_notice(), now=T, symbol="ABC", market_evidence=evidence(age_seconds=31), require_market_evidence=True)
        self.assertEqual(r.decision, "DENY")

    def test_required_market_evidence_without_symbol_denies(self):
        r = authorize_bundle(BASE, full_notice(), now=T, market_evidence=evidence(), require_market_evidence=True)
        self.assertEqual(r.decision, "DENY")

    def test_decision_hash_is_deterministic(self):
        a = authorize_bundle(BASE, full_notice(), now=T)
        b = authorize_bundle(BASE, full_notice(), now=T)
        self.assertEqual(a.decision_sha256, b.decision_sha256)


if __name__ == "__main__":
    unittest.main()
