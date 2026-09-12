import unittest

from semantic_health import HealthSample, HealthState, assess


class SemanticHealthTests(unittest.TestCase):
    def test_healthy_requires_process_endpoint_freshness_and_capacity(self):
        result = assess(
            HealthSample(
                process_alive=True,
                endpoint_accepting=True,
                telemetry_age_seconds=1.0,
                telemetry_max_age_seconds=5.0,
                operational_entities=6,
                expected_min_entities=1,
            )
        )
        self.assertEqual(result.state, HealthState.HEALTHY)
        self.assertTrue(result.service_ready)
        self.assertEqual(result.reasons, ())

    def test_dead_process_is_unavailable(self):
        result = assess(
            HealthSample(
                process_alive=False,
                endpoint_accepting=True,
                telemetry_age_seconds=1.0,
                telemetry_max_age_seconds=5.0,
            )
        )
        self.assertEqual(result.state, HealthState.UNAVAILABLE)
        self.assertFalse(result.service_ready)
        self.assertEqual(result.reasons, ("process_not_alive",))

    def test_live_router_that_cannot_accept_is_degraded(self):
        result = assess(
            HealthSample(
                process_alive=True,
                endpoint_accepting=False,
                telemetry_age_seconds=1.0,
                telemetry_max_age_seconds=5.0,
            )
        )
        self.assertEqual(result.state, HealthState.DEGRADED)
        self.assertIn("endpoint_not_accepting", result.reasons)

    def test_live_process_with_frozen_telemetry_is_stale(self):
        result = assess(
            HealthSample(
                process_alive=True,
                endpoint_accepting=True,
                telemetry_age_seconds=10.0,
                telemetry_max_age_seconds=5.0,
            )
        )
        self.assertEqual(result.state, HealthState.STALE)
        self.assertIn("telemetry_stale", result.reasons)

    def test_missing_telemetry_is_stale(self):
        result = assess(
            HealthSample(
                process_alive=True,
                endpoint_accepting=True,
                telemetry_age_seconds=None,
                telemetry_max_age_seconds=5.0,
            )
        )
        self.assertEqual(result.state, HealthState.STALE)
        self.assertIn("telemetry_missing", result.reasons)

    def test_live_fleet_with_no_operational_robot_is_degraded(self):
        result = assess(
            HealthSample(
                process_alive=True,
                endpoint_accepting=True,
                telemetry_age_seconds=1.0,
                telemetry_max_age_seconds=5.0,
                operational_entities=0,
                expected_min_entities=1,
            )
        )
        self.assertEqual(result.state, HealthState.DEGRADED)
        self.assertIn("operational_entity_count_below_minimum", result.reasons)

    def test_stale_takes_precedence_over_degraded_reasons(self):
        result = assess(
            HealthSample(
                process_alive=True,
                endpoint_accepting=False,
                telemetry_age_seconds=10.0,
                telemetry_max_age_seconds=5.0,
                operational_entities=0,
                expected_min_entities=1,
            )
        )
        self.assertEqual(result.state, HealthState.STALE)
        self.assertEqual(
            set(result.reasons),
            {
                "endpoint_not_accepting",
                "telemetry_stale",
                "operational_entity_count_below_minimum",
            },
        )

    def test_negative_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            assess(
                HealthSample(
                    process_alive=True,
                    endpoint_accepting=True,
                    telemetry_age_seconds=1.0,
                    telemetry_max_age_seconds=-1.0,
                )
            )


if __name__ == "__main__":
    unittest.main()
