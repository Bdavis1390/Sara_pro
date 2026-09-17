import unittest
from pathlib import Path

from ws_cae.crypto_portfolio import build

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "ws_cae/examples"


class CryptoPortfolioTests(unittest.TestCase):
    def test_portfolio_identifies_repeated_blocker_roles(self):
        result = build([
            EXAMPLES / "system_stablecoin.json",
            EXAMPLES / "system_bridged_asset.json",
            EXAMPLES / "system_exchange_balance.json",
            EXAMPLES / "system_rollup_asset.json",
        ])
        self.assertTrue(result["all_valid"])
        self.assertEqual(result["portfolio_state"], "PORTFOLIO_HAS_CRITICAL_MIGRATION_BLOCKERS")
        self.assertEqual(result["weakest_readiness_state"], "CLASSICAL_DEPENDENCY")
        self.assertEqual(result["asset_count"], 4)
        self.assertIn("ASSET_ISSUER_ADMIN", result["blocking_role_counts"])
        self.assertIn("BRIDGE_MESSAGING", result["blocking_role_counts"])
        self.assertIn("EXCHANGE_WITHDRAWAL", result["blocking_role_counts"])
        self.assertIn("PROTOCOL_ADMIN", result["blocking_role_counts"])

    def test_native_coin_reference_remains_partial_not_fully_deployed(self):
        result = build([EXAMPLES / "system_native_coin.json"])
        self.assertEqual(result["portfolio_state"], "PORTFOLIO_PARTIAL_PQ_READINESS")
        self.assertEqual(result["weakest_readiness_state"], "CRYPTO_AGILE")


if __name__ == "__main__":
    unittest.main()
