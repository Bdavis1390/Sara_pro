from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ws_cae.scitt_statement import build_chain_statement
from ws_cae.transparency_root import build_root, verify_inclusion


class TestTransparencyRoot(unittest.TestCase):
    def _statement(self, path: str):
        patch = json.loads(Path(path).read_text(encoding="utf-8"))
        return build_chain_statement(patch, "did:web:publisher.example", "2026-09-13T22:00:00Z")

    def test_four_subject_root_is_deterministic_and_all_inclusions_verify(self):
        statements = [
            self._statement("ws_cae/examples/algorand.patch.json"),
            self._statement("ws_cae/examples/bitcoin-qsb.patch.json"),
            self._statement("ws_cae/examples/ethereum.patch.json"),
            self._statement("ws_cae/examples/sui.patch.json"),
        ]
        root_a = build_root(statements)
        root_b = build_root(list(reversed(statements)))
        self.assertEqual(root_a["root_sha256"], root_b["root_sha256"])
        by_id = {s["subject"]["id"]: s for s in statements}
        for entry in root_a["entries"]:
            self.assertTrue(verify_inclusion(by_id[entry["subject_id"]], entry["proof"], root_a["root_sha256"]))

    def test_tampered_statement_does_not_verify(self):
        statement = self._statement("ws_cae/examples/ethereum.patch.json")
        root = build_root([statement])
        tampered = copy.deepcopy(statement)
        tampered["claims"]["implementation_maturity"] = "MAINNET"
        self.assertFalse(verify_inclusion(tampered, root["entries"][0]["proof"], root["root_sha256"]))

    def test_duplicate_subject_fails_closed(self):
        statement = self._statement("ws_cae/examples/ethereum.patch.json")
        with self.assertRaises(ValueError):
            build_root([statement, copy.deepcopy(statement)])


if __name__ == "__main__":
    unittest.main()
