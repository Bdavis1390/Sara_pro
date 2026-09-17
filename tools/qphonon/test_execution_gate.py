from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from execution_gate import evaluate_execution


NOW = datetime(2026, 9, 17, 23, 0, 0, tzinfo=timezone.utc)
EXPERIMENT_DIGEST = "1" * 64
CONFIG_DIGEST = "2" * 64
APPROVAL_ID = "123e4567-e89b-42d3-b456-426614174001"

PRIME_PASS = {
    "authorized": True,
    "disposition": "READY_FOR_HUMAN_APPROVAL",
    "reasons": [],
    "requires_human_approval": True,
}


def valid_approval() -> dict:
    return {
        "approved": True,
        "approval_id": APPROVAL_ID,
        "approver": "authorized-human-reviewer",
        "approval_attestation_verified": True,
        "experiment_digest": EXPERIMENT_DIGEST,
        "config_digest": CONFIG_DIGEST,
        "issued_at_utc": "2026-09-17T22:59:00Z",
        "expires_at_utc": "2026-09-17T23:10:00Z",
    }


class ExecutionGateTests(unittest.TestCase):
    def test_verified_approval_passes(self) -> None:
        decision = evaluate_execution(
            PRIME_PASS,
            valid_approval(),
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            now=NOW,
        )
        self.assertTrue(decision.executable)
        self.assertEqual(decision.disposition, "EXECUTION_ALLOWED")

    def test_unverified_attestation_blocks(self) -> None:
        approval = valid_approval()
        approval["approval_attestation_verified"] = False
        decision = evaluate_execution(
            PRIME_PASS,
            approval,
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.executable)
        self.assertIn("APPROVAL_ATTESTATION_NOT_VERIFIED", decision.reasons)

    def test_reused_approval_id_blocks(self) -> None:
        decision = evaluate_execution(
            PRIME_PASS,
            valid_approval(),
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            seen_approval_ids={APPROVAL_ID},
            now=NOW,
        )
        self.assertFalse(decision.executable)
        self.assertIn("APPROVAL_REPLAY_DETECTED", decision.reasons)

    def test_expired_approval_blocks(self) -> None:
        approval = valid_approval()
        approval["issued_at_utc"] = "2026-09-17T22:40:00Z"
        approval["expires_at_utc"] = "2026-09-17T22:50:00Z"
        decision = evaluate_execution(
            PRIME_PASS,
            approval,
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.executable)
        self.assertIn("APPROVAL_EXPIRED", decision.reasons)

    def test_overlong_approval_lifetime_blocks(self) -> None:
        approval = valid_approval()
        approval["issued_at_utc"] = "2026-09-17T22:50:00Z"
        approval["expires_at_utc"] = "2026-09-17T23:20:01Z"
        decision = evaluate_execution(
            PRIME_PASS,
            approval,
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.executable)
        self.assertIn("APPROVAL_LIFETIME_INVALID", decision.reasons)

    def test_wrong_experiment_digest_blocks(self) -> None:
        approval = valid_approval()
        approval["experiment_digest"] = "3" * 64
        decision = evaluate_execution(
            PRIME_PASS,
            approval,
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.executable)
        self.assertIn("EXPERIMENT_DIGEST_MISMATCH", decision.reasons)

    def test_wrong_config_digest_blocks(self) -> None:
        approval = valid_approval()
        approval["config_digest"] = "4" * 64
        decision = evaluate_execution(
            PRIME_PASS,
            approval,
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.executable)
        self.assertIn("CONFIG_DIGEST_MISMATCH", decision.reasons)

    def test_prime_failure_blocks_even_with_human_approval(self) -> None:
        prime = dict(PRIME_PASS)
        prime["authorized"] = False
        prime["disposition"] = "CHARACTERIZE_OR_ABORT"
        decision = evaluate_execution(
            prime,
            valid_approval(),
            experiment_digest=EXPERIMENT_DIGEST,
            config_digest=CONFIG_DIGEST,
            now=NOW,
        )
        self.assertFalse(decision.executable)
        self.assertIn("PRIME_SOFTWARE_GATE_NOT_PASSED", decision.reasons)


if __name__ == "__main__":
    unittest.main()
