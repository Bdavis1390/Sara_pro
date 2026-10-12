import unittest

from migration_timeline_collision import (
    ExternalRiskHorizon,
    ProtocolTransitionSchedule,
    assess_timeline_collision,
)


class MigrationTimelineCollisionTests(unittest.TestCase):
    def test_bip361_nominal_five_year_sunset_exceeds_2028_planning_horizon(self):
        bip361 = ProtocolTransitionSchedule(
            name="BIP-361 full sunset",
            source="https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki",
            years_to_full_transition=5.0,
            consensus_activated=False,
            schedule_status="Draft",
        )
        ionq_2028 = ExternalRiskHorizon(
            name="IonQ 2028 roadmap collision horizon",
            source="https://www.ionq.com/roadmap",
            target_year=2028,
            demonstrated=False,
            evidence_class="vendor_roadmap",
        )

        result = assess_timeline_collision(bip361, ionq_2028, current_year=2026)
        self.assertEqual(result.collision_state, "BEST_CASE_TRANSITION_EXCEEDS_RISK_HORIZON")
        self.assertEqual(result.best_case_margin_years, -3.0)
        self.assertEqual(result.schedule_state, "NOT_CONSENSUS_ACTIVE")
        self.assertEqual(result.horizon_state, "FORWARD_PLANNING_EVIDENCE")
        self.assertEqual(result.urgency, "ACCELERATE_PARALLEL_MIGRATION_AND_ACTIVATION_PLANNING")
        self.assertTrue(any("optimistic upper bound" in reason for reason in result.reasons))
        self.assertTrue(any("not demonstrated" in reason.lower() for reason in result.reasons))

    def test_roadmap_horizon_never_becomes_qday_claim(self):
        schedule = ProtocolTransitionSchedule("transition", "test", 1.0, consensus_activated=True)
        horizon = ExternalRiskHorizon("roadmap", "test", 2028, demonstrated=False)
        result = assess_timeline_collision(schedule, horizon, current_year=2026)
        self.assertEqual(result.horizon_state, "FORWARD_PLANNING_EVIDENCE")
        self.assertNotIn("QDAY", result.collision_state)

    def test_positive_margin_is_not_emergency(self):
        schedule = ProtocolTransitionSchedule("transition", "test", 1.0, consensus_activated=True)
        horizon = ExternalRiskHorizon("horizon", "test", 2030, demonstrated=False)
        result = assess_timeline_collision(schedule, horizon, current_year=2026)
        self.assertEqual(result.best_case_margin_years, 3.0)
        self.assertEqual(result.collision_state, "BEST_CASE_TRANSITION_WITHIN_RISK_HORIZON")
        self.assertEqual(result.urgency, "MONITOR_AND_VALIDATE_MIGRATION_CAPACITY")


if __name__ == "__main__":
    unittest.main()
