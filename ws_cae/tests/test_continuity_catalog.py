import json
import tempfile
import unittest
from pathlib import Path

from ws_cae.cli import InputError
from ws_cae.continuity_catalog import build


class ContinuityCatalogTests(unittest.TestCase):
    def _patch(self, path: Path, chain: str):
        path.write_text(json.dumps({
            "spec":"WS-CAE-CHAIN-PATCH-1",
            "chain":chain,
            "profile":{
                "ecosystem":chain,
                "adapter_class":"REFERENCE",
                "implementation_maturity":"TESTNET",
                "stable_authority_id":True,
                "authenticator_replaceable":True,
                "pq_authorization_state":"PQ_NON_MAINNET",
                "policy_state_documented":True,
                "recovery_state_documented":True,
                "domain_binding_documented":True,
                "evidence_state_documented":True,
                "consensus_pq_state":"CLASSICAL_OR_UNPROVEN",
                "protocol_commitment_state":"GOVERNANCE_SELECTED"
            },
            "evidence":[{"label":"Example","url":"https://example.com/evidence","claim":"Synthetic test evidence."}]
        }))

    def test_snapshot_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td)/"a.json", Path(td)/"b.json"
            self._patch(a, "Alpha")
            self._patch(b, "Beta")
            x = build([a,b], version="1", as_of="2026-09-13")
            y = build([b,a], version="1", as_of="2026-09-13")
            self.assertEqual(x["snapshot_id"], y["snapshot_id"])
            self.assertEqual(x["manifest_count"], 2)

    def test_duplicate_subject_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td)/"a.json", Path(td)/"b.json"
            self._patch(a, "Alpha")
            self._patch(b, "Alpha")
            with self.assertRaises(InputError):
                build([a,b], version="1", as_of="2026-09-13")


if __name__ == "__main__":
    unittest.main()
