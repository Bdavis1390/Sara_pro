import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ws_cae.patch_diff import compare, fingerprint


class PatchDiffTests(unittest.TestCase):
    def write(self, payload):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(payload, handle)
        return Path(handle.name)

    def test_fingerprint_is_order_independent_for_objects(self):
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        self.assertEqual(fingerprint(a), fingerprint(b))

    def test_change_detection_tracks_maturity_and_commitment_separately(self):
        source = json.loads((ROOT / "ws_cae/examples/ethereum.patch.json").read_text(encoding="utf-8"))
        updated = json.loads(json.dumps(source))
        updated["profile"]["implementation_maturity"] = "TESTNET"
        updated["profile"]["protocol_commitment_state"] = "MAINNET"
        result = compare(self.write(source), self.write(updated))
        by_field = {item["field"]: item for item in result["profile_changes"]}
        self.assertEqual(by_field["implementation_maturity"]["before"], "DEVNET")
        self.assertEqual(by_field["implementation_maturity"]["after"], "TESTNET")
        self.assertEqual(by_field["protocol_commitment_state"]["before"], "FORK_SCHEDULED")
        self.assertEqual(by_field["protocol_commitment_state"]["after"], "MAINNET")
        self.assertTrue(by_field["implementation_maturity"]["risk_relevant"])
        self.assertTrue(by_field["protocol_commitment_state"]["risk_relevant"])

    def test_evidence_changes_are_visible(self):
        source = json.loads((ROOT / "ws_cae/examples/sui.patch.json").read_text(encoding="utf-8"))
        updated = json.loads(json.dumps(source))
        updated["evidence"] = updated["evidence"][:1]
        result = compare(self.write(source), self.write(updated))
        self.assertTrue(result["changed"])
        self.assertEqual(len(result["evidence_removed"]), 1)


if __name__ == "__main__":
    unittest.main()
