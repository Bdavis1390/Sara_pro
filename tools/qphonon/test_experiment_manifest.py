from __future__ import annotations

from dataclasses import replace
import math
import unittest

from experiment_manifest import freeze_manifest, verify_manifest


EXPERIMENT_ID = "123e4567-e89b-42d3-a456-426614174111"
CONFIG = {"mode": "synthetic", "temperature_limit_k": 0.125}
PARAMETERS = {"g1_hz": 3_000_000.0, "t2_s": 5e-6}
ACCEPTANCE = {"holdout_required": True, "cooperativity_min": 1.0}


def make_manifest():
    return freeze_manifest(
        experiment_id=EXPERIMENT_ID,
        created_at_utc="2026-09-17T23:00:00Z",
        model_version="qphonon-twin-v0.2",
        claims_state="SIMULATED_ONLY",
        config=CONFIG,
        parameter_snapshot=PARAMETERS,
        acceptance_criteria=ACCEPTANCE,
    )


class ManifestTests(unittest.TestCase):
    def test_frozen_manifest_verifies(self) -> None:
        manifest = make_manifest()
        self.assertTrue(manifest.frozen)
        self.assertEqual(
            verify_manifest(
                manifest,
                config=CONFIG,
                parameter_snapshot=PARAMETERS,
                acceptance_criteria=ACCEPTANCE,
            ),
            [],
        )

    def test_config_tamper_is_detected(self) -> None:
        changed = dict(CONFIG)
        changed["temperature_limit_k"] = 0.5
        errors = verify_manifest(
            make_manifest(),
            config=changed,
            parameter_snapshot=PARAMETERS,
            acceptance_criteria=ACCEPTANCE,
        )
        self.assertIn("CONFIG_DIGEST_MISMATCH", errors)

    def test_parameter_tamper_is_detected(self) -> None:
        changed = dict(PARAMETERS)
        changed["g1_hz"] = 9_000_000.0
        errors = verify_manifest(
            make_manifest(),
            config=CONFIG,
            parameter_snapshot=changed,
            acceptance_criteria=ACCEPTANCE,
        )
        self.assertIn("PARAMETER_SNAPSHOT_DIGEST_MISMATCH", errors)

    def test_acceptance_criteria_tamper_is_detected(self) -> None:
        changed = dict(ACCEPTANCE)
        changed["cooperativity_min"] = 0.1
        errors = verify_manifest(
            make_manifest(),
            config=CONFIG,
            parameter_snapshot=PARAMETERS,
            acceptance_criteria=changed,
        )
        self.assertIn("ACCEPTANCE_CRITERIA_DIGEST_MISMATCH", errors)

    def test_manifest_digest_tamper_is_detected(self) -> None:
        manifest = replace(make_manifest(), model_version="changed-after-freeze")
        errors = verify_manifest(
            manifest,
            config=CONFIG,
            parameter_snapshot=PARAMETERS,
            acceptance_criteria=ACCEPTANCE,
        )
        self.assertIn("MANIFEST_DIGEST_MISMATCH", errors)

    def test_invalid_experiment_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            freeze_manifest(
                experiment_id="not-a-uuid",
                created_at_utc="2026-09-17T23:00:00Z",
                model_version="qphonon-twin-v0.2",
                claims_state="SIMULATED_ONLY",
                config=CONFIG,
                parameter_snapshot=PARAMETERS,
                acceptance_criteria=ACCEPTANCE,
            )

    def test_invalid_timestamp_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            freeze_manifest(
                experiment_id=EXPERIMENT_ID,
                created_at_utc="not-a-timeZ",
                model_version="qphonon-twin-v0.2",
                claims_state="SIMULATED_ONLY",
                config=CONFIG,
                parameter_snapshot=PARAMETERS,
                acceptance_criteria=ACCEPTANCE,
            )

    def test_invalid_claims_state_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            freeze_manifest(
                experiment_id=EXPERIMENT_ID,
                created_at_utc="2026-09-17T23:00:00Z",
                model_version="qphonon-twin-v0.2",
                claims_state="TOTALLY_PROVEN",
                config=CONFIG,
                parameter_snapshot=PARAMETERS,
                acceptance_criteria=ACCEPTANCE,
            )

    def test_nan_parameter_is_rejected_by_canonicalization(self) -> None:
        changed = dict(PARAMETERS)
        changed["g1_hz"] = math.nan
        with self.assertRaises(ValueError):
            freeze_manifest(
                experiment_id=EXPERIMENT_ID,
                created_at_utc="2026-09-17T23:00:00Z",
                model_version="qphonon-twin-v0.2",
                claims_state="SIMULATED_ONLY",
                config=CONFIG,
                parameter_snapshot=changed,
                acceptance_criteria=ACCEPTANCE,
            )


if __name__ == "__main__":
    unittest.main()
