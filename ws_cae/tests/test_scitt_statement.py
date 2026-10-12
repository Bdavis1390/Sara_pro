from __future__ import annotations

import json
import unittest
from pathlib import Path

from ws_cae.scitt_statement import MEDIA_TYPE, SPEC, build_chain_statement, canonical_json, sha256_hex


class TestSCITTStatement(unittest.TestCase):
    def test_statement_is_deterministic_and_evidence_bound(self):
        patch_path = Path("ws_cae/examples/ethereum.patch.json")
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
        statement = build_chain_statement(patch, "did:web:example.org", "2026-09-13T22:00:00Z")

        self.assertEqual(statement["spec"], SPEC)
        self.assertEqual(statement["media_type"], MEDIA_TYPE)
        self.assertEqual(statement["subject"]["name"], "Ethereum")
        self.assertEqual(statement["subject"]["source_patch_sha256"], sha256_hex(patch))
        self.assertEqual(statement["claims"]["implementation_maturity"], "DEVNET")
        self.assertEqual(statement["claims"]["protocol_commitment_state"], "FORK_SCHEDULED")
        self.assertEqual(canonical_json(statement), canonical_json(statement))

    def test_requires_evidence(self):
        with self.assertRaises(ValueError):
            build_chain_statement({"chain": "Example", "profile": {}, "evidence": []}, "did:web:example.org")


if __name__ == "__main__":
    unittest.main()
