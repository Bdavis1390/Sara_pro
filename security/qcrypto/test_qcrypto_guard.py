import unittest

from qcrypto_guard import (
    AttackEstimate,
    ClassicalDecoderEvidence,
    HardwareRoadmapTarget,
    PlatformMaturityEvidence,
    QECEvidence,
    assess,
    assess_full_stack_convergence,
    assess_qec_bridge,
    assess_roadmap_collision,
)


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

    def test_measured_low_overhead_qec_does_not_become_attack_projection(self):
        luo = AttackEstimate(
            name="Luo 835q",
            source="arXiv:2607.13816",
            full_attack=True,
            logical_qubits=835,
            toffoli_gates=1_927_282_688,
        )
        helix = QECEvidence(
            name="Quantinuum C4-Helix",
            source="arXiv:2609.03194",
            physical_qubits=20,
            logical_qubits=2,
            code_distance=6,
            logical_memory_error_per_cycle=4.6e-5,
            logical_clifford_error=2.8e-4,
            postselection_used=False,
        )
        bridge = assess_qec_bridge(luo, helix)
        self.assertEqual(bridge.evidence_state, "HARDWARE_VALIDATED_QEC_WITHOUT_POSTSELECTION")
        self.assertEqual(bridge.physical_per_logical, 10.0)
        self.assertEqual(bridge.codeblock_floor_physical_qubits, 8350)
        self.assertEqual(bridge.attack_projection_state, "CROSS_ARCHITECTURE_PROJECTION_BLOCKED")
        self.assertGreaterEqual(len(bridge.blocking_gaps), 4)

    def test_qec_codeblock_floor_is_not_physical_attack_estimate(self):
        attack = AttackEstimate(
            name="complete attack",
            source="test",
            full_attack=True,
            logical_qubits=1000,
            toffoli_gates=1_000_000,
        )
        qec = QECEvidence(
            name="measured code",
            source="test",
            physical_qubits=20,
            logical_qubits=2,
            logical_memory_error_per_cycle=1e-5,
        )
        bridge = assess_qec_bridge(attack, qec)
        self.assertEqual(bridge.codeblock_floor_physical_qubits, 10000)
        self.assertNotEqual(bridge.attack_projection_state, "MODEL_READY_NOT_PRODUCTION_BREAK")
        self.assertTrue(any("overhead" in gap.lower() for gap in bridge.blocking_gaps))

    def test_ionq_2028_roadmap_overlaps_its_attack_envelope_without_claiming_break(self):
        attack = AttackEstimate(
            name="IonQ Walking Cat",
            source="arXiv:2609.05625",
            full_attack=True,
            logical_qubits=1450,
            toffoli_gates=40_000_000,
            physical_qubits=19_397,
            runtime_seconds=25.7 * 86400,
        )
        roadmap = HardwareRoadmapTarget(
            vendor="IonQ",
            source="https://www.ionq.com/roadmap",
            target_year=2028,
            physical_qubits=20_000,
            logical_qubits=1600,
            logical_error_rate=1e-7,
            same_architecture_family=True,
            demonstrated=False,
        )
        result = assess_roadmap_collision(attack, roadmap, current_year=2026, migration_years=1.5)
        self.assertEqual(result.collision_state, "SAME_ARCHITECTURE_ATTACK_ENVELOPE_COLLISION")
        self.assertEqual(result.evidence_state, "VENDOR_ROADMAP_TARGET")
        self.assertEqual(result.logical_headroom, 150)
        self.assertEqual(result.physical_headroom, 603)
        self.assertEqual(result.urgency, "ACCELERATE_MIGRATION_VALIDATION")
        self.assertTrue(any("forward-looking" in reason for reason in result.reasons))

    def test_roadmap_collision_with_negative_migration_margin_flags_schedule_not_qday(self):
        attack = AttackEstimate(
            name="IonQ Walking Cat",
            source="test",
            full_attack=True,
            logical_qubits=1450,
            toffoli_gates=40_000_000,
            physical_qubits=19_397,
            runtime_seconds=25.7 * 86400,
        )
        roadmap = HardwareRoadmapTarget(
            vendor="IonQ",
            source="test",
            target_year=2028,
            physical_qubits=20_000,
            logical_qubits=1600,
            same_architecture_family=True,
        )
        result = assess_roadmap_collision(attack, roadmap, current_year=2026, migration_years=3)
        self.assertEqual(result.urgency, "MIGRATION_SCHEDULE_AT_RISK")
        self.assertLessEqual(result.migration_margin_years, 0)
        self.assertNotEqual(result.evidence_state, "DEMONSTRATED_HARDWARE_CAPABILITY")

    def test_2027_ionq_target_is_near_luo_width_but_not_a_complete_collision(self):
        luo = AttackEstimate(
            name="Luo 835q",
            source="arXiv:2607.13816",
            full_attack=True,
            logical_qubits=835,
            toffoli_gates=1_927_282_688,
        )
        roadmap = HardwareRoadmapTarget(
            vendor="IonQ",
            source="https://www.ionq.com/roadmap",
            target_year=2027,
            physical_qubits=10_000,
            logical_qubits=800,
            same_architecture_family=False,
        )
        result = assess_roadmap_collision(luo, roadmap, current_year=2026)
        self.assertEqual(result.collision_state, "NEAR_LOGICAL_WIDTH_COLLISION")
        self.assertEqual(result.logical_headroom, -35)
        self.assertEqual(result.evidence_state, "VENDOR_ROADMAP_TARGET")

    def test_full_stack_convergence_detects_multiple_planes_without_claiming_attack_ready(self):
        attack = AttackEstimate(
            name="IonQ Walking Cat",
            source="arXiv:2609.05625",
            full_attack=True,
            logical_qubits=1457,
            toffoli_gates=39_000_000,
            physical_qubits=19_397,
            runtime_seconds=25.7 * 86400,
        )
        roadmap = HardwareRoadmapTarget(
            vendor="IonQ",
            source="https://www.ionq.com/roadmap",
            target_year=2028,
            physical_qubits=20_000,
            logical_qubits=1600,
            same_architecture_family=True,
        )
        platform = PlatformMaturityEvidence(
            vendor="IonQ",
            source="IonQ Superion 256 announcement",
            platform="Superion 256 / Walking Cat lineage",
            physical_qubits=256,
            qpu_fabricated=True,
            qubits_trapped_or_operated=True,
            customer_orders_open=True,
            customer_delivery_year=2027,
            qec_component_validated_on_related_hardware=True,
            same_architecture_family=True,
            target_scale_demonstrated=False,
        )
        decoder = ClassicalDecoderEvidence(
            name="Generalized qLDPC predecoder FPGA design",
            source="arXiv:2605.03180",
            code_family="qLDPC / bivariate bicycle",
            supported_logical_qubits=1200,
            implementation_kind="FPGA_DESIGN",
            demonstrated_hardware=False,
            workload_processed_fraction=0.90,
            decoder_utilization_reduction=3963,
            exact_attack_code_compatible=False,
            attack_specific_integration=False,
        )
        result = assess_full_stack_convergence(
            attack, roadmap, platform, decoder, current_year=2026, migration_years=1.5
        )
        self.assertEqual(result.convergence_state, "MULTI_PLANE_CONVERGENCE_SIGNAL")
        self.assertEqual(result.platform_maturity_state, "PROTOTYPE_PLATFORM_PLUS_RELATED_QEC_VALIDATED")
        self.assertEqual(result.decoder_state, "PROPOSED_DECODER_CAPACITY_ONLY")
        self.assertGreater(result.decoder_capacity_ratio, 0.80)
        self.assertEqual(result.urgency, "ACCELERATE_MIGRATION_VALIDATION")
        self.assertTrue(any("not demonstrated" in gap.lower() for gap in result.blocking_gaps))

    def test_proposed_decoder_capacity_can_never_be_treated_as_integrated_attack_decoder(self):
        decoder = ClassicalDecoderEvidence(
            name="proposed decoder",
            source="test",
            code_family="qLDPC",
            supported_logical_qubits=100000,
            implementation_kind="CRYO_ASIC_DESIGN",
            demonstrated_hardware=False,
            exact_attack_code_compatible=True,
            attack_specific_integration=True,
        )
        attack = AttackEstimate("attack", "test", True, 1000, 1_000_000, 20000, 86400)
        roadmap = HardwareRoadmapTarget("vendor", "test", 2028, 20000, 1600, same_architecture_family=True)
        platform = PlatformMaturityEvidence(
            "vendor", "test", "prototype", 256, True, True, True, 2027, True, True, False
        )
        result = assess_full_stack_convergence(attack, roadmap, platform, decoder, current_year=2026)
        self.assertEqual(result.decoder_state, "PROPOSED_DECODER_CAPACITY_ONLY")
        self.assertNotIn("ATTACK_INTEGRATED", result.decoder_state)

    def test_target_scale_platform_required_before_prototype_can_be_called_target_scale(self):
        platform = PlatformMaturityEvidence(
            vendor="IonQ",
            source="test",
            platform="Superion 256",
            physical_qubits=256,
            qpu_fabricated=True,
            qubits_trapped_or_operated=True,
            qec_component_validated_on_related_hardware=True,
            target_scale_demonstrated=False,
        )
        attack = AttackEstimate("attack", "test", True, 1457, 39_000_000, 19_397, 25.7 * 86400)
        roadmap = HardwareRoadmapTarget("IonQ", "test", 2028, 20_000, 1600, same_architecture_family=True)
        decoder = ClassicalDecoderEvidence("decoder", "test", "qLDPC", 1200, "FPGA_DESIGN")
        result = assess_full_stack_convergence(attack, roadmap, platform, decoder, current_year=2026)
        self.assertNotEqual(result.platform_maturity_state, "TARGET_SCALE_DEMONSTRATED")
        self.assertTrue(any("attack-scale" in gap.lower() for gap in result.blocking_gaps))


if __name__ == "__main__":
    unittest.main()
