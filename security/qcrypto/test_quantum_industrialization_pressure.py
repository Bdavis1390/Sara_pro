import unittest

from quantum_industrialization_pressure import IndustrializationEvidence, assess_quantum_industrialization


class QuantumIndustrializationPressureTests(unittest.TestCase):
    def test_attack_and_defense_co_acceleration(self):
        evidence = IndustrializationEvidence(
            name="US quantum industrialization plus financial PQ transition",
            source="official public evidence",
            federal_quantum_funding_active=True,
            manufacturing_scale_program_active=True,
            fault_tolerant_vendor_awards_active=True,
            financial_sector_pq_transition_active=True,
            digital_assets_in_defensive_scope=True,
        )
        result = assess_quantum_industrialization(evidence)
        self.assertEqual(result.strategic_state, "ATTACK_DEFENSE_CO_ACCELERATION")
        self.assertEqual(result.offensive_side_state, "INDUSTRIAL_SCALE_ENABLERS_ACTIVE")
        self.assertEqual(result.defensive_side_state, "COORDINATED_FINANCIAL_PQ_MIGRATION_ACTIVE")
        self.assertEqual(result.urgency, "COMPRESS_MIGRATION_TIMELINES_AND_TRACK_INDUSTRIAL_CAPACITY")
        self.assertTrue(any("No production cryptographic break" in gap for gap in result.blocking_gaps))

    def test_funding_does_not_equal_qday(self):
        evidence = IndustrializationEvidence(
            name="funding only",
            source="test",
            federal_quantum_funding_active=True,
            manufacturing_scale_program_active=True,
            fault_tolerant_vendor_awards_active=True,
        )
        result = assess_quantum_industrialization(evidence)
        self.assertEqual(result.strategic_state, "QUANTUM_INDUSTRIALIZATION_ACCELERATING")
        self.assertTrue(any("No production cryptanalytic attack machine" in gap for gap in result.blocking_gaps))

    def test_defensive_coordination_alone_is_separate(self):
        evidence = IndustrializationEvidence(
            name="defense only",
            source="test",
            financial_sector_pq_transition_active=True,
            digital_assets_in_defensive_scope=True,
        )
        result = assess_quantum_industrialization(evidence)
        self.assertEqual(result.strategic_state, "DEFENSIVE_SECTOR_MIGRATION_ACCELERATING")
        self.assertEqual(result.offensive_side_state, "INDUSTRIAL_SCALE_ENABLERS_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
