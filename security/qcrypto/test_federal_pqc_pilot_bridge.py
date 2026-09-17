import unittest

from cbom_inventory import CryptoAsset
from federal_pqc_pilot_bridge import CLAIM_BOUNDARY, portfolio_pilot_targets, recommend_pilot_target


class FederalPQCPilotBridgeTests(unittest.TestCase):
    def _asset(self, **overrides):
        values = dict(
            asset_id="asset-001",
            system_name="Example System",
            owner="Example Owner",
            algorithm_family="ECC",
            cryptographic_role="authentication",
            evidence_source="inventory://example",
            last_verified="2026-09-13",
        )
        values.update(overrides)
        return CryptoAsset(**values)

    def test_incomplete_evidence_cannot_enter_dry_run(self):
        target = recommend_pilot_target(self._asset(evidence_source=""), human_approved=True)
        self.assertEqual(target.pilot_entry_stage, "H0_EVIDENCE_QUALIFICATION_BLOCKED")
        self.assertFalse(target.live_value_authorized)
        self.assertFalse(target.conformance_established)
        self.assertFalse(target.federal_compliance_established)

    def test_high_value_asset_targets_c3_but_does_not_claim_conformance(self):
        target = recommend_pilot_target(self._asset(high_value_asset=True, pqc_ready=False))
        self.assertEqual(target.priority, "P0_MIGRATION_PRIORITY")
        self.assertEqual(target.target_cae_profile, "CAE-C3_DIVERSIFIED_HIGH_VALUE_AUTHORITY")
        self.assertEqual(target.pilot_entry_stage, "H0_EVIDENCE_QUALIFICATION")
        self.assertFalse(target.conformance_established)

    def test_human_approval_allows_only_zero_value_entry(self):
        target = recommend_pilot_target(
            self._asset(high_impact_system=True, pqc_ready=False),
            human_approved=True,
        )
        self.assertEqual(target.pilot_entry_stage, "H1_ZERO_VALUE_DRY_RUN")
        self.assertFalse(target.live_value_authorized)
        self.assertTrue(target.human_approval_required)

    def test_modernization_target_is_c2(self):
        target = recommend_pilot_target(self._asset(pqc_ready=False, crypto_agile=False))
        self.assertEqual(target.priority, "P2_MODERNIZATION_PRIORITY")
        self.assertEqual(target.target_cae_profile, "CAE-C2_RECOVERABLE_DOMAIN_BOUND")

    def test_monitor_target_is_c1_and_still_not_live(self):
        target = recommend_pilot_target(self._asset(pqc_ready=True, crypto_agile=True), human_approved=True)
        self.assertEqual(target.priority, "P3_MONITOR")
        self.assertEqual(target.target_cae_profile, "CAE-C1_CRYPTO_AGILE_AUTHORITY")
        self.assertEqual(target.pilot_entry_stage, "H1_ZERO_VALUE_DRY_RUN")
        self.assertFalse(target.live_value_authorized)

    def test_portfolio_never_self_awards_compliance_or_live_authority(self):
        assets = (
            self._asset(asset_id="critical", high_value_asset=True),
            self._asset(asset_id="monitor", pqc_ready=True, crypto_agile=True),
        )
        result = portfolio_pilot_targets(assets, approved_asset_ids=frozenset({"critical", "monitor"}))
        self.assertEqual(result["h1_count"], 2)
        self.assertEqual(result["live_value_authorized_count"], 0)
        self.assertEqual(result["conformance_established_count"], 0)
        self.assertEqual(result["federal_compliance_established_count"], 0)
        self.assertEqual(result["claim_boundary"], CLAIM_BOUNDARY)


if __name__ == "__main__":
    unittest.main()
