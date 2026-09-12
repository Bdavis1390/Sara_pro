import unittest

from qcrypto_guard import AttackEstimate, assess


class QCryptoGuardTests(unittest.TestCase):
    def test_low_width_high_gate_full_attack_stays_q1_without_runtime(self):
        luo = AttackEstimate(
            name="Luo 835q",
            source="arXiv:2607.13816",
            full_attack=True,
            logical_qubits=835,
            toffoli_gates=1_927_282_688,
        )
        result = assess(luo, exposure_seconds=365 * 86400, warning_days=180, migration_days=365)
        self.assertEqual(result.threat_level, "Q1")
        self.assertEqual(result.width_band, "VERY_LOW_WIDTH")
        self.assertTrue(any("high Toffoli" in reason for reason in result.reasons))

    def test_ionq_runtime_overlaps_long_exposure(self):
        ionq = AttackEstimate(
            name="IonQ 25.7d",
            source="arXiv:2609.05625",
            full_attack=True,
            logical_qubits=1450,
            toffoli_gates=40_000_000,
            physical_qubits=19_397,
            runtime_seconds=25.7 * 86400,
        )
        result = assess(ionq, exposure_seconds=365 * 86400, warning_days=365, migration_days=180)
        self.assertEqual(result.threat_level, "Q2")
        self.assertLess(result.attack_exposure_ratio, 1.0)

    def test_negative_migration_margin_escalates_q2_to_q3(self):
        estimate = AttackEstimate(
            name="modeled fast complete attack",
            source="test",
            full_attack=True,
            logical_qubits=1200,
            toffoli_gates=90_000_000,
            runtime_seconds=300,
        )
        result = assess(estimate, exposure_seconds=3600, warning_days=30, migration_days=90)
        self.assertEqual(result.threat_level, "Q3")
        self.assertLess(result.migration_margin_days, 0)

    def test_subroutine_result_cannot_escalate_from_width_alone(self):
        subroutine = AttackEstimate(
            name="point addition only",
            source="test",
            full_attack=False,
            logical_qubits=700,
            toffoli_gates=500_000,
            runtime_seconds=1,
        )
        result = assess(subroutine, exposure_seconds=365 * 86400, warning_days=1, migration_days=365)
        self.assertEqual(result.threat_level, "Q0")

    def test_q4_requires_explicit_production_break_evidence(self):
        demonstrated = AttackEstimate(
            name="authorized controlled production break",
            source="test",
            full_attack=True,
            logical_qubits=100,
            toffoli_gates=100,
            production_break_demonstrated=True,
        )
        result = assess(demonstrated)
        self.assertEqual(result.threat_level, "Q4")
        self.assertEqual(result.claim_state, "PRODUCTION_BREAK_DEMONSTRATED")


if __name__ == "__main__":
    unittest.main()
