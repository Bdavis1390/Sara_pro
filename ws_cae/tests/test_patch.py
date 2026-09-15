import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ws_cae.patch_cli import run


class ChainPatchTests(unittest.TestCase):
    def write(self, payload):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(payload, handle)
        return Path(handle.name)

    def test_reference_patches(self):
        expected = {
            "algorand.patch.json": "PQ_MAINNET",
            "ethereum.patch.json": "PLUGGABLE_AUTH_ONLY",
            "sui.patch.json": "PLUGGABLE_AUTH_ONLY",
            "bitcoin-qsb.patch.json": "PQ_MAINNET_LIMITED",
        }
        for filename, pq_state in expected.items():
            with self.subTest(filename=filename):
                result = run(ROOT / "ws_cae/examples" / filename)
                self.assertTrue(result["patch"]["valid"])
                self.assertEqual(
                    result["patch"]["profile_assessment"]["pq_authorization_state"],
                    pq_state,
                )

    def test_protocol_commitment_is_separate_from_maturity(self):
        result = run(ROOT / "ws_cae/examples/ethereum.patch.json")
        profile = result["patch"]["profile_assessment"]
        self.assertEqual(profile["maturity_state"], "IMPLEMENTATION_DEVNET")
        self.assertEqual(profile["protocol_commitment_state"], "FORK_SCHEDULED")

    def test_chain_mismatch_fails_closed(self):
        raw = json.loads((ROOT / "ws_cae/examples/ethereum.patch.json").read_text(encoding="utf-8"))
        raw["chain"] = "OtherChain"
        result = run(self.write(raw))
        self.assertFalse(result["patch"]["valid"])

    def test_non_https_evidence_fails_closed(self):
        raw = json.loads((ROOT / "ws_cae/examples/ethereum.patch.json").read_text(encoding="utf-8"))
        raw["evidence"][0]["url"] = "http://example.invalid/evidence"
        result = run(self.write(raw))
        self.assertFalse(result["patch"]["valid"])


if __name__ == "__main__":
    unittest.main()
