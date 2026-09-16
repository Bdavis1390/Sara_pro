import unittest

from cbom_inventory import CryptoAsset
from federal_pqc_control_plane import (
    AUDIT_PROJECTION_SCHEMA,
    CLAIM_BOUNDARY,
    audit_projection,
    evaluate_asset,
    portfolio_status,
)


class FederalPQCControlPlaneTests(unittest.TestCase):
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

    def test_incomplete_evidence_is_blocked_before_policy(self):
        asset = self._asset(evidence_source="")
        result = evaluate_asset(asset, human_approved=True)
        self.assertEqual(result.echo_state, "ECHO_REJECTED_INCOMPLETE_EVIDENCE")
        self.assertEqual(result.prime_state, "PRIME_NOT_EVALUATED")
        self.assertEqual(result.sara_state, "SARA_BLOCKED")
        self.assertFalse(result.migration_executed)

    def test_high_value_asset_requires_human_approval(self):
        asset = self._asset(high_value_asset=True, pqc_ready=False)
        result = evaluate_asset(asset)
        self.assertEqual(result.priority, "P0_MIGRATION_PRIORITY")
        self.assertEqual(result.prime_state, "PRIME_RECOMMENDS_PRIORITY_MIGRATION_PLAN")
        self.assertEqual(result.sara_state, "SARA_AWAITING_HUMAN_APPROVAL")
        self.assertTrue(result.human_approval_required)
        self.assertFalse(result.migration_executed)

    def test_human_approval_authorizes_plan_not_execution(self):
        asset = self._asset(high_impact_system=True, pqc_ready=False)
        result = evaluate_asset(asset, human_approved=True)
        self.assertEqual(result.sara_state, "SARA_PLAN_AUTHORIZED")
        self.assertEqual(result.overwatch_state, "OVERWATCH_TRACK_AUTHORIZED_PLAN")
        self.assertFalse(result.migration_executed)
        self.assertEqual(result.claim_boundary, CLAIM_BOUNDARY)

    def test_monitor_state_still_preserves_human_gate(self):
        asset = self._asset(pqc_ready=True, crypto_agile=True)
        result = evaluate_asset(asset)
        self.assertEqual(result.priority, "P3_MONITOR")
        self.assertEqual(result.prime_state, "PRIME_RECOMMENDS_MONITOR")
        self.assertEqual(result.sara_state, "SARA_AWAITING_HUMAN_APPROVAL")
        self.assertFalse(result.migration_executed)

    def test_audit_projection_is_data_only_and_claims_controlled(self):
        decision = evaluate_asset(self._asset(high_value_asset=True), human_approved=True)
        projection = audit_projection(decision, correlation_id="QCRYPTO-TEST-001")
        self.assertEqual(projection["schema"], AUDIT_PROJECTION_SCHEMA)
        self.assertEqual(projection["asset_id"], "asset-001")
        self.assertEqual(projection["sara_state"], "SARA_PLAN_AUTHORIZED")
        self.assertEqual(projection["correlation_id"], "QCRYPTO-TEST-001")
        self.assertFalse(projection["migration_executed"])
        self.assertFalse(projection["execution_authority"])
        self.assertFalse(projection["live_value_authorized"])
        self.assertFalse(projection["federal_compliance_established"])
        self.assertFalse(projection["ws_cae_conformance_established"])
        self.assertEqual(projection["claim_boundary"], CLAIM_BOUNDARY)

    def test_audit_projection_rejects_empty_correlation_id(self):
        decision = evaluate_asset(self._asset())
        with self.assertRaises(ValueError):
            audit_projection(decision, correlation_id="")

    def test_portfolio_status_counts_governed_states(self):
        assets = (
            self._asset(asset_id="critical", high_value_asset=True),
            self._asset(asset_id="monitor", pqc_ready=True, crypto_agile=True),
            self._asset(asset_id="gap", evidence_source=""),
        )
        status = portfolio_status(assets, approved_asset_ids=frozenset({"critical"}))
        self.assertEqual(status["asset_count"], 3)
        self.assertEqual(status["authorized_plan_count"], 1)
        self.assertEqual(status["pending_approval_count"], 1)
        self.assertEqual(status["evidence_gap_count"], 1)
        self.assertEqual(status["migration_execution_count"], 0)
        self.assertEqual(status["claim_boundary"], CLAIM_BOUNDARY)


if __name__ == "__main__":
    unittest.main()
