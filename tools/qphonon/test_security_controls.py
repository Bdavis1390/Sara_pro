from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import unittest

from security_controls import compute_event_digest, verify_echo_event


NOW = datetime(2026, 9, 17, 23, 0, 0, tzinfo=timezone.utc)
CONFIG_DIGEST = "a" * 64
PREVIOUS_DIGEST = "b" * 64


def valid_event() -> dict:
    event = {
        "schema": "WS-QPHONON-ECHO-EVENT-V0.2",
        "event_id": "123e4567-e89b-42d3-a456-426614174000",
        "event_sequence": 7,
        "event_time_utc": "2026-09-17T23:00:00Z",
        "raw_data_hash": "c" * 64,
        "config_digest": CONFIG_DIGEST,
        "previous_event_digest": PREVIOUS_DIGEST,
        "event_digest": "0" * 64,
        "model_version": "qphonon-twin-test",
        "prior": {},
        "posterior": {},
        "experiment_proposed": {"kind": "synthetic_test"},
        "expected_information_gain": 0.5,
        "prime_decision": {
            "authorized": True,
            "disposition": "READY_FOR_HUMAN_APPROVAL",
            "reasons": [],
            "requires_human_approval": True,
        },
        "control_waveform_or_parameters": {},
        "environmental_state": {"physical_hardware": False},
        "measurement_result": {"value": 1.0},
        "model_discrepancy": {"pass": True},
        "claims_state": "SIMULATED_ONLY",
    }
    event["event_digest"] = compute_event_digest(event)
    return event


class SecurityControlTests(unittest.TestCase):
    def test_valid_event_passes(self) -> None:
        decision = verify_echo_event(
            valid_event(),
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertTrue(decision.passed)
        self.assertEqual(decision.disposition, "INTEGRITY_VERIFIED")

    def test_post_record_tamper_is_detected(self) -> None:
        event = valid_event()
        event["measurement_result"]["value"] = 2.0
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("EVENT_DIGEST_MISMATCH", decision.reasons)

    def test_replayed_event_id_is_rejected(self) -> None:
        event = valid_event()
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            seen_event_ids={event["event_id"]},
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("EVENT_REPLAY_DETECTED", decision.reasons)

    def test_stale_event_is_rejected(self) -> None:
        event = valid_event()
        event["event_time_utc"] = (NOW - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        event["event_digest"] = compute_event_digest(event)
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("EVENT_STALE", decision.reasons)

    def test_future_event_is_rejected(self) -> None:
        event = valid_event()
        event["event_time_utc"] = (NOW + timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
        event["event_digest"] = compute_event_digest(event)
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("EVENT_FROM_FUTURE", decision.reasons)

    def test_wrong_config_digest_is_rejected(self) -> None:
        event = valid_event()
        decision = verify_echo_event(
            event,
            expected_config_digest="d" * 64,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("CONFIG_DIGEST_MISMATCH", decision.reasons)

    def test_broken_event_chain_is_rejected(self) -> None:
        event = valid_event()
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest="e" * 64,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("EVENT_CHAIN_MISMATCH", decision.reasons)

    def test_unknown_top_level_field_is_rejected(self) -> None:
        event = valid_event()
        event["unexpected"] = "payload"
        event["event_digest"] = compute_event_digest(event)
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("UNKNOWN_TOP_LEVEL_FIELDS", decision.reasons)

    def test_missing_required_field_is_rejected(self) -> None:
        event = valid_event()
        del event["raw_data_hash"]
        event["event_digest"] = compute_event_digest(event)
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("MISSING_REQUIRED_FIELDS", decision.reasons)

    def test_noncanonical_hash_format_is_rejected(self) -> None:
        event = valid_event()
        event["raw_data_hash"] = "ABC"
        event["event_digest"] = compute_event_digest(event)
        decision = verify_echo_event(
            event,
            expected_config_digest=CONFIG_DIGEST,
            expected_previous_event_digest=PREVIOUS_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.passed)
        self.assertIn("RAW_DATA_HASH_INVALID", decision.reasons)


if __name__ == "__main__":
    unittest.main()
