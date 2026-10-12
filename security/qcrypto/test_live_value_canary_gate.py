import unittest

from live_value_canary_gate import LiveValueCanaryEvidence, assess_live_value_canary


class LiveValueCanaryGateTests(unittest.TestCase):
    def base(self, **overrides):
        data = dict(
            candidate_chain="Algorand MainNet",
            native_pq_authorization_live=True,
            single_native_asset_scope=True,
            bridge_free_scope=True,
            fresh_dedicated_canary_account=True,
            wallet_and_tooling_interop_validated=True,
            chain_adapter_testnet_validated=True,
            recovery_path_precommitted=True,
            recovery_drill_passed=True,
            independent_review_complete=True,
            critical_findings_closed=True,
            immutable_evidence_logging=True,
            monitoring_and_pause_ready=True,
            bounded_value_policy_defined=True,
            deployment_expiry_defined=True,
            explicit_human_approval_present=False,
            live_execution_receipt_present=False,
            consensus_layer_pq=False,
        )
        data.update(overrides)
        return LiveValueCanaryEvidence(**data)

    def test_full_controls_stop_at_human_approval_gate(self):
        result = assess_live_value_canary(self.base())
        self.assertEqual(result.readiness_state, "LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL")
        self.assertEqual(result.execution_state, "NO_LIVE_VALUE_EXECUTED_BY_THIS_CONTROL")

    def test_approval_enables_policy_state_but_does_not_execute(self):
        result = assess_live_value_canary(self.base(explicit_human_approval_present=True))
        self.assertEqual(result.readiness_state, "LVC_AUTHORIZED_FOR_BOUNDED_EXECUTION")
        self.assertEqual(result.execution_state, "NO_LIVE_VALUE_EXECUTED_BY_THIS_CONTROL")

    def test_execution_receipt_without_approval_is_invalid(self):
        result = assess_live_value_canary(self.base(live_execution_receipt_present=True))
        self.assertEqual(result.execution_state, "INVALID_EXECUTION_EVIDENCE_REQUIRES_REVIEW")

    def test_bridge_dependency_blocks_minimized_scope(self):
        result = assess_live_value_canary(self.base(bridge_free_scope=False))
        self.assertEqual(result.scope_state, "SCOPE_NOT_MINIMIZED")
        self.assertEqual(result.readiness_state, "LVC_SCOPE_DESIGN_REQUIRED")

    def test_missing_recovery_drill_blocks_live_readiness(self):
        result = assess_live_value_canary(self.base(recovery_drill_passed=False))
        self.assertEqual(result.readiness_state, "LVC_INTEGRATION_VALIDATION_REQUIRED")

    def test_live_receipt_is_only_recorded_after_complete_authorization(self):
        result = assess_live_value_canary(self.base(explicit_human_approval_present=True, live_execution_receipt_present=True))
        self.assertEqual(result.execution_state, "EXTERNAL_LIVE_CANARY_EXECUTION_RECORDED")
        self.assertTrue(any("consensus" in gap.lower() for gap in result.blockers))


if __name__ == "__main__":
    unittest.main()
