import unittest

from cbom_inventory import CryptoAsset, inventory_summary, priority_band, validate_asset


class CBOMInventoryTests(unittest.TestCase):
    def test_missing_provenance_blocks_priority_claim(self):
        asset = CryptoAsset(
            asset_id="A-1",
            system_name="example",
            owner="team",
            algorithm_family="ECC",
            cryptographic_role="key establishment",
        )
        self.assertIn("evidence_source", validate_asset(asset))
        self.assertEqual(priority_band(asset), "INCOMPLETE_EVIDENCE")

    def test_hva_not_pqc_ready_is_p0(self):
        asset = CryptoAsset(
            asset_id="A-2",
            system_name="example-hva",
            owner="team",
            algorithm_family="ECC",
            cryptographic_role="key establishment",
            high_value_asset=True,
            pqc_ready=False,
            crypto_agile=False,
            evidence_source="authorized-internal-inventory",
            last_verified="2026-09-12",
        )
        self.assertEqual(priority_band(asset), "P0_MIGRATION_PRIORITY")

    def test_sensitive_long_lived_not_pqc_ready_is_p1(self):
        asset = CryptoAsset(
            asset_id="A-3",
            system_name="example-sensitive",
            owner="team",
            algorithm_family="RSA",
            cryptographic_role="digital signature",
            highly_sensitive_data=True,
            mission_sensitive_after_2030=True,
            pqc_ready=False,
            crypto_agile=True,
            evidence_source="authorized-internal-inventory",
            last_verified="2026-09-12",
        )
        self.assertEqual(priority_band(asset), "P1_MIGRATION_PRIORITY")

    def test_ready_and_agile_asset_is_monitor(self):
        asset = CryptoAsset(
            asset_id="A-4",
            system_name="example-ready",
            owner="team",
            algorithm_family="PQC",
            cryptographic_role="key establishment",
            pqc_ready=True,
            crypto_agile=True,
            evidence_source="authorized-internal-inventory",
            last_verified="2026-09-12",
        )
        self.assertEqual(priority_band(asset), "P3_MONITOR")
        summary = inventory_summary((asset,))
        self.assertEqual(summary["asset_count"], 1)
        self.assertEqual(
            summary["claim_boundary"],
            "INTERNAL_CBOM_MODEL_NOT_FEDERAL_COMPLIANCE",
        )


if __name__ == "__main__":
    unittest.main()
