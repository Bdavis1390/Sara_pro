from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest
from pathlib import Path

from security_controls import compute_event_digest, verify_echo_event


ROOT = Path(__file__).resolve().parents[2]
PROFILE = json.loads((ROOT / "config" / "ws_qphonon_security_v0_2.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 9, 17, 23, 0, 0, tzinfo=timezone.utc)
CONFIG_DIGEST = "a" * 64
PREVIOUS_DIGEST = "b" * 64


def base_event() -> dict:
    event = {
        "schema": "WS-QPHONON-ECHO-EVENT-V0.2",
        "event_id": "123e4567-e89b-42d3-a456-426614174222",
        "event_sequence": 9,
        "event_time_utc": "2026-09-17T23:00:00Z",
        "raw_data_hash": "c" * 64,
        "config_digest": CONFIG_DIGEST,
        "previous_event_digest": PREVIOUS_DIGEST,
        "event_digest": "0" * 64,
        "model_version": "mutation-sweep",
        "prior": {},
        "posterior": {},
        "experiment_proposed": {"kind": "synthetic"},
        "expected_information_gain": 0.1,
        "prime_decision": {
            "authorized": True,
            "disposition": "READY_FOR_HUMAN_APPROVAL",
            "reasons": [],
            "requires_human_approval": True,
        },
        "control_waveform_or_parameters": {},
        "environmental_state": {"physical_hardware": False},
        "measurement_result": {"value": 0},
        "model_discrepancy": {"pass": True},
        "claims_state": "SIMULATED_ONLY",
    }
    event["event_digest"] = compute_event_digest(event)
    return event


class SecurityMutationSweepTests(unittest.TestCase):
    def test_at_least_100_adversarial_event_mutations_fail_closed(self) -> None:
        count = 0

        for index in range(40):
            event = base_event()
            event["measurement_result"] = {"value": index + 1}
            with self.subTest(kind="tamper", index=index):
                decision = verify_echo_event(
                    event,
                    expected_config_digest=CONFIG_DIGEST,
                    expected_previous_event_digest=PREVIOUS_DIGEST,
                    now=NOW,
                )
                self.assertFalse(decision.passed)
                self.assertIn("EVENT_DIGEST_MISMATCH", decision.reasons)
            count += 1

        for index in range(40):
            event = base_event()
            event[f"unexpected_{index}"] = index
            event["event_digest"] = compute_event_digest(event)
            with self.subTest(kind="unknown_field", index=index):
                decision = verify_echo_event(
                    event,
                    expected_config_digest=CONFIG_DIGEST,
                    expected_previous_event_digest=PREVIOUS_DIGEST,
                    now=NOW,
                )
                self.assertFalse(decision.passed)
                self.assertIn("UNKNOWN_TOP_LEVEL_FIELDS", decision.reasons)
            count += 1

        wrong_digests = ["d" * 64, "e" * 64, "f" * 64, "0" * 64]
        for index in range(40):
            event = base_event()
            event["config_digest"] = wrong_digests[index % len(wrong_digests)]
            event["event_digest"] = compute_event_digest(event)
            with self.subTest(kind="config_binding", index=index):
                decision = verify_echo_event(
                    event,
                    expected_config_digest=CONFIG_DIGEST,
                    expected_previous_event_digest=PREVIOUS_DIGEST,
                    now=NOW,
                )
                self.assertFalse(decision.passed)
                self.assertIn("CONFIG_DIGEST_MISMATCH", decision.reasons)
            count += 1

        self.assertGreaterEqual(count, PROFILE["minimum_adversarial_mutation_cases"])


if __name__ == "__main__":
    unittest.main()
