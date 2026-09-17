import unittest

from financial_sector_coordination import SectorCoordinationEvidence, assess_sector_coordination


class FinancialSectorCoordinationTests(unittest.TestCase):
    def test_treasury_g7_digital_asset_coordination_is_sector_transition(self):
        evidence = SectorCoordinationEvidence(
            name="Treasury Quantum-Readiness Task Force + G7 roadmap",
            source="official",
            federal_policy_active=True,
            public_private_task_force_active=True,
            digital_assets_explicitly_in_scope=True,
            third_party_vendor_readiness_workstream=True,
            cross_border_g7_roadmap=True,
            crypto_specific_binding_deadline=False,
            blockchain_pq_activation_required=True,
            qday_demonstrated=False,
        )
        result = assess_sector_coordination(evidence)
        self.assertEqual(result.coordination_state, "FINANCIAL_SECTOR_COORDINATED_PQ_TRANSITION")
        self.assertEqual(result.digital_asset_state, "DIGITAL_ASSETS_EXPLICITLY_IN_SCOPE")
        self.assertEqual(result.mandate_state, "COORDINATION_WITHOUT_CRYPTO_SPECIFIC_BINDING_DEADLINE")
        self.assertEqual(result.urgency, "ALIGN_CHAIN_CUSTODY_STABLECOIN_BRIDGE_MIGRATION_WITH_SECTOR_PROGRAM")
        self.assertTrue(any("chain-native" in gap for gap in result.blocking_gaps))
        self.assertTrue(any("Q-day" in gap for gap in result.blocking_gaps))

    def test_task_force_does_not_create_crypto_deadline(self):
        evidence = SectorCoordinationEvidence(
            name="sector coordination",
            source="official",
            public_private_task_force_active=True,
            digital_assets_explicitly_in_scope=True,
        )
        result = assess_sector_coordination(evidence)
        self.assertNotEqual(result.mandate_state, "CRYPTO_SPECIFIC_BINDING_DEADLINE_PRESENT")


if __name__ == "__main__":
    unittest.main()
