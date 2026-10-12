from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ws_cae.scitt_statement import build_chain_statement
from ws_cae.transparency_timeline import build_timeline


class TestTransparencyTimeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = json.loads(Path("ws_cae/examples/ethereum.patch.json").read_text(encoding="utf-8"))

    def statement(self, issuer: str, time: str = "2026-09-13T22:00:00Z"):
        return build_chain_statement(self.patch, issuer, time)

    def test_agreement_has_no_conflict(self):
        a = self.statement("did:web:issuer-a.example")
        b = self.statement("did:web:issuer-b.example")
        timeline = build_timeline([a, b])
        self.assertEqual(timeline["statement_count"], 2)
        self.assertEqual(timeline["subject_count"], 1)
        self.assertEqual(timeline["conflicts"], [])

    def test_cross_issuer_disagreement_is_preserved(self):
        a = self.statement("did:web:issuer-a.example")
        b = copy.deepcopy(self.statement("did:web:issuer-b.example"))
        b["claims"]["implementation_maturity"] = "TESTNET"
        timeline = build_timeline([a, b])
        kinds = [item["kind"] for item in timeline["conflicts"]]
        self.assertIn("CROSS_ISSUER_DISAGREEMENT", kinds)

    def test_same_issuer_equivocation_is_preserved(self):
        a = self.statement("did:web:issuer-a.example")
        b = copy.deepcopy(a)
        b["claims"]["pq_authorization_state"] = "PQ_NON_MAINNET"
        timeline = build_timeline([a, b])
        kinds = [item["kind"] for item in timeline["conflicts"]]
        self.assertIn("ISSUER_EQUIVOCATION", kinds)

    def test_invalid_time_fails_closed(self):
        statement = self.statement("did:web:issuer-a.example")
        statement["observed_at"] = "not-a-date"
        with self.assertRaises(ValueError):
            build_timeline([statement])


if __name__ == "__main__":
    unittest.main()
