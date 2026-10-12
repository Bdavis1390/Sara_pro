import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ws_cae.catalog import build


class CatalogTests(unittest.TestCase):
    def patches(self):
        base = ROOT / "ws_cae/examples"
        return [
            base / "algorand.patch.json",
            base / "ethereum.patch.json",
            base / "sui.patch.json",
            base / "bitcoin-qsb.patch.json",
        ]

    def test_four_chain_catalog_is_normalized(self):
        result = build(self.patches())
        self.assertEqual(result["chain_count"], 4)
        self.assertEqual(
            [row["chain"] for row in result["chains"]],
            ["Algorand", "Bitcoin", "Ethereum", "Sui"],
        )
        by_chain = {row["chain"]: row for row in result["chains"]}
        self.assertEqual(by_chain["Algorand"]["pq_authorization_state"], "PQ_MAINNET")
        self.assertEqual(by_chain["Bitcoin"]["pq_authorization_state"], "PQ_MAINNET_LIMITED")
        self.assertEqual(by_chain["Ethereum"]["protocol_commitment_state"], "FORK_SCHEDULED")
        self.assertEqual(by_chain["Sui"]["protocol_commitment_state"], "GOVERNANCE_SELECTED")

    def test_fork_committed_policy_distinguishes_catalog(self):
        policy = ROOT / "ws_cae/examples/fork_committed_policy.json"
        result = build(self.patches(), policy)
        by_chain = {row["chain"]: row for row in result["chains"]}
        self.assertTrue(by_chain["Algorand"]["policy_pass"])
        self.assertTrue(by_chain["Ethereum"]["policy_pass"])
        self.assertFalse(by_chain["Sui"]["policy_pass"])
        self.assertFalse(by_chain["Bitcoin"]["policy_pass"])
        self.assertFalse(result["all_policy_pass"])


if __name__ == "__main__":
    unittest.main()
