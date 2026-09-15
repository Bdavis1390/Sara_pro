import unittest
from pathlib import Path

from ws_cae.crypto_system import ComponentState, CryptoSystemPatch, assess_system
from ws_cae.crypto_system_cli import run

ROOT = Path(__file__).resolve().parents[2]


class CryptoSystemTests(unittest.TestCase):
    def test_weakest_critical_dependency_controls_system_state(self):
        patch = CryptoSystemPatch(
            "synthetic",
            (
                ComponentState("CHAIN_AUTHORITY", "chain", "PQ_DEPLOYED", True, True),
                ComponentState("ASSET_ISSUER_ADMIN", "issuer", "CLASSICAL_DEPENDENCY", True, True),
                ComponentState("WALLET_DEVICE", "wallet", "CRYPTO_AGILE", True, True),
            ),
        )
        result = assess_system(patch)
        self.assertTrue(result.valid)
        self.assertEqual(result.weakest_readiness_state, "CLASSICAL_DEPENDENCY")
        self.assertEqual(result.system_state, "SYSTEM_MIGRATION_BLOCKED_BY_CRITICAL_DEPENDENCY")
        self.assertIn("ASSET_ISSUER_ADMIN:issuer", result.blocking_components)

    def test_noncritical_component_does_not_lower_system_state(self):
        patch = CryptoSystemPatch(
            "synthetic",
            (
                ComponentState("CHAIN_AUTHORITY", "chain", "PQ_DEPLOYED", True, True),
                ComponentState("WALLET_DEVICE", "optional-wallet", "UNASSESSED", False, True),
            ),
        )
        result = assess_system(patch)
        self.assertTrue(result.valid)
        self.assertEqual(result.system_state, "ALL_DECLARED_CRITICAL_DEPENDENCIES_PQ_DEPLOYED")

    def test_namespaced_extension_role_supports_unfamiliar_architecture(self):
        patch = CryptoSystemPatch(
            "synthetic",
            (
                ComponentState("CHAIN_AUTHORITY", "chain", "PQ_DEPLOYED", True, True),
                ComponentState("X_PRIVACY_PROOF_COORDINATOR", "custom-component", "PQ_PARTIAL", True, True),
            ),
        )
        result = assess_system(patch)
        self.assertTrue(result.valid)
        self.assertEqual(result.weakest_readiness_state, "PQ_PARTIAL")
        self.assertIn("X_PRIVACY_PROOF_COORDINATOR:custom-component", result.blocking_components)

    def test_unnamespaced_unknown_role_fails_closed(self):
        patch = CryptoSystemPatch(
            "synthetic",
            (ComponentState("MYSTERY_ROLE", "unknown", "PQ_DEPLOYED", True, True),),
        )
        self.assertFalse(assess_system(patch).valid)

    def test_missing_evidence_fails_closed(self):
        patch = CryptoSystemPatch(
            "synthetic",
            (ComponentState("CHAIN_AUTHORITY", "chain", "PQ_DEPLOYED", True, False),),
        )
        self.assertFalse(assess_system(patch).valid)

    def test_synthetic_stablecoin_shows_chain_readiness_is_insufficient(self):
        result = run(ROOT / "ws_cae/examples/system_stablecoin.json")
        assessment = result["assessment"]
        self.assertTrue(assessment["valid"])
        self.assertEqual(assessment["weakest_readiness_state"], "CLASSICAL_DEPENDENCY")

    def test_synthetic_bridge_shows_cross_chain_dependency(self):
        result = run(ROOT / "ws_cae/examples/system_bridged_asset.json")
        assessment = result["assessment"]
        self.assertEqual(assessment["system_state"], "SYSTEM_MIGRATION_BLOCKED_BY_CRITICAL_DEPENDENCY")

    def test_reference_examples_cover_major_crypto_asset_paths(self):
        names = [
            "system_native_coin.json",
            "system_stablecoin.json",
            "system_bridged_asset.json",
            "system_exchange_balance.json",
            "system_rollup_asset.json",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(run(ROOT / "ws_cae/examples" / name)["assessment"]["valid"])


if __name__ == "__main__":
    unittest.main()
