"""Negative tests for the opt-in synthetic verify/reserve/execute controller."""
from __future__ import annotations

import base64
import copy
import hashlib
import shutil
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from authorized_synthetic_execution import (
    AuthorizedSyntheticExecutionError,
    execute_authorized_synthetic,
)
from bounded_execution import (
    ExecutionCustodyError, calculated_output, verify_receipt,
)
from local_grant_ledger import LocalGrantLedger, LocalGrantLedgerError
from scientific_prime_authorization import (
    ACTION, SCHEMA, SCOPE, ScientificPrimeAuthorizationError,
    canonical_scientific_authorization,
)


def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class AuthorizedSyntheticExecutionTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        for file in ("config.json", "input.json"):
            shutil.copy(ROOT / "examples/bounded_exec" / file, self.root / file)
        self.ledger = LocalGrantLedger(self.root / "private-ledger")
        self.key = Ed25519PrivateKey.generate()
        pub = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.fingerprint = hashlib.sha256(pub).hexdigest()
        self.verifier = PrimeSentinelVerifier(public_keys_b64url={"science-test": encode(pub)})
        self.instant = datetime.now(timezone.utc)
        self.issued_at = (self.instant - timedelta(seconds=20)).isoformat(timespec='seconds').replace('+00:00', 'Z')
        self.expires_at = (self.instant + timedelta(minutes=5)).isoformat(timespec='seconds').replace('+00:00', 'Z')
        self.grant = {
            "schema": SCHEMA,
            "issuer": "PRIME_SENTINEL",
            "action": ACTION,
            "scope": SCOPE,
            "key_id": "science-test",
            "authorization_id": "science-grant-1001",
            "nonce": "science-unique-nonce-1001",
            "claim_id": "WS-LOCAL-SYNTHETIC-001",
            "prereg_sha256": "a" * 64,
            "run_id": "run01",
            "config_sha256": hashlib.sha256((self.root/"config.json").read_bytes()).hexdigest(),
            "input_sha256": hashlib.sha256((self.root/"input.json").read_bytes()).hexdigest(),
            "executor_sha256": hashlib.sha256((ROOT/"bounded_execution.py").read_bytes()).hexdigest(),
            "max_samples": 4,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "signature_b64url": "",
        }
        self.sign()

    def sign(self):
        self.grant["signature_b64url"] = encode(
            self.key.sign(canonical_scientific_authorization(self.grant))
        )

    def execute(self, **overrides):
        args = dict(
            root=self.root,
            assertion=self.grant,
            config_path="config.json",
            input_path="input.json",
            ledger=self.ledger,
            prime_verifier=self.verifier,
            expected_claim_id="WS-LOCAL-SYNTHETIC-001",
            expected_prereg_sha256="a" * 64,
            expected_signer_key_fingerprint_sha256=self.fingerprint,
        )
        args.update(overrides)
        return execute_authorized_synthetic(**args)

    def test_signed_grant_consumed_before_bounded_execution(self):
        result = self.execute()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["output"]["samples"], [-4, 2, 5, 14])
        self.assertTrue(result["prime_signature_verified_for_this_run"])
        self.assertTrue(result["grant_consumed_in_local_ledger"])
        self.assertTrue(result["bounded_synthetic_execution_performed"])
        self.assertEqual(self.ledger.state("science-grant-1001"), "FINISHED")
        self.assertEqual(verify_receipt(self.root, result["receipt"])["status"], "PASS")
        self.assertEqual(result["receipt"]["authorization"]["authorization_id"], "science-grant-1001")
        for field in (
            "independent_preexecution_freeze_verified", "independent_process_attestation_verified",
            "echo_checkpoint_witness_verified", "external_timestamp_verified", "scientific_claim_proven",
        ):
            self.assertIs(result[field], False)

    def test_grant_replay_after_completion_rejected(self):
        self.execute()
        with self.assertRaises(AuthorizedSyntheticExecutionError):
            self.execute()
        self.assertEqual(self.ledger.state("science-grant-1001"), "FINISHED")

    def test_invalid_signature_rejected_before_execution(self):
        self.grant["signature_b64url"] = "A" * 86
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))
        self.assertFalse((self.root/"runs").exists())

    def test_wrong_external_prereg_pin_rejected_before_execution(self):
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.execute(expected_prereg_sha256="1" * 64)
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_revoked_prime_key_rejected_before_execution(self):
        pub = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        revoked = PrimeSentinelVerifier(
            public_keys_b64url={"science-test": encode(pub)},
            revoked_key_ids={"science-test"},
        )
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.execute(prime_verifier=revoked)
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_incorrect_config_bytes_not_executed(self):
        (self.root/"config.json").write_text('{"operation":"affine_v1","scale":9,"offset":1}\n')
        with self.assertRaisesRegex(ScientificPrimeAuthorizationError, "configuration"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_incorrect_input_bytes_not_executed(self):
        (self.root/"input.json").write_text('{"samples":[11]}\n')
        with self.assertRaisesRegex(ScientificPrimeAuthorizationError, "input"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_executor_digest_mismatch_rejected(self):
        self.grant["executor_sha256"] = "0" * 64
        self.sign()
        with self.assertRaisesRegex(ScientificPrimeAuthorizationError, "executor"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_wrong_authorized_operation_cannot_execute(self):
        self.grant["action"] = "REQUALIFICATION_RELEASE"
        self.sign()
        with self.assertRaisesRegex(ScientificPrimeAuthorizationError, "action"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_over_budget_samples_rejected(self):
        self.grant["max_samples"] = 2
        self.sign()
        with self.assertRaisesRegex(ScientificPrimeAuthorizationError, "budget"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_expired_signature_rejected(self):
        self.grant["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat(timespec="seconds").replace("+00:00", "Z")
        self.sign()
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_invalid_run_id_prevents_reservation(self):
        self.grant["run_id"] = "../escape"
        with self.assertRaisesRegex(AuthorizedSyntheticExecutionError, "run ID"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_existing_output_identity_prevents_reservation(self):
        (self.root/"runs").mkdir()
        (self.root/"runs/run01.output.json").write_text("stale")
        with self.assertRaisesRegex(AuthorizedSyntheticExecutionError, "already exists"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_symlinked_run_directory_rejected(self):
        other = self.root / "other"
        other.mkdir()
        (self.root/"runs").symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(AuthorizedSyntheticExecutionError, "symlink"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_config_symlink_rejected(self):
        (self.root/"config.json").unlink()
        (self.root/"config.json").symlink_to(ROOT/"examples/bounded_exec/config.json")
        with self.assertRaisesRegex(ExecutionCustodyError, "symlink"):
            self.execute()
        self.assertIsNone(self.ledger.state("science-grant-1001"))

    def test_failed_calculation_leaves_grant_reserved_not_reusable(self):
        with patch("authorized_synthetic_execution.calculated_output", side_effect=RuntimeError("injected process failure")):
            with self.assertRaisesRegex(RuntimeError, "injected process failure"):
                self.execute()
        self.assertEqual(self.ledger.state("science-grant-1001"), "RESERVED")
        with self.assertRaises(LocalGrantLedgerError):
            self.execute()

    def test_no_computation_occurs_before_grant_reservation(self):
        observed = []
        real_calc = calculated_output
        def check_order(config, inputs):
            observed.append(self.ledger.state("science-grant-1001"))
            return real_calc(config, inputs)
        with patch("authorized_synthetic_execution.calculated_output", side_effect=check_order):
            self.execute()
        self.assertEqual(observed, ["RESERVED"])

    def test_same_byte_objects_are_verified_and_executed(self):
        import authorized_synthetic_execution as controller
        real_reserve = controller.verify_and_reserve_science_grant
        real_calc = calculated_output
        snapshots = []
        def reserve_then_check(*args, **kwargs):
            snapshots.extend((kwargs["expected_config_bytes"], kwargs["expected_input_bytes"]))
            return real_reserve(*args, **kwargs)
        def calc_then_check(config, inputs):
            self.assertIs(config, snapshots[0])
            self.assertIs(inputs, snapshots[1])
            return real_calc(config, inputs)
        with patch("authorized_synthetic_execution.verify_and_reserve_science_grant", side_effect=reserve_then_check):
            with patch("authorized_synthetic_execution.calculated_output", side_effect=calc_then_check):
                self.execute()
        self.assertEqual(len(snapshots), 2)

    def test_two_concurrent_executions_cannot_consume_same_grant_twice(self):
        def attempt(_):
            try:
                self.execute()
                return "PASS"
            except (AuthorizedSyntheticExecutionError, LocalGrantLedgerError, FileExistsError):
                return "BLOCK"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(results.count("PASS"), 1)
        self.assertEqual(results.count("BLOCK"), 1)
        self.assertEqual(self.ledger.state("science-grant-1001"), "FINISHED")

    def test_local_receipt_tamper_detected(self):
        result = self.execute()
        receipt = copy.deepcopy(result["receipt"])
        receipt["authorization"]["grant_sha256"] = "0" * 64
        with self.assertRaisesRegex(ExecutionCustodyError, "receipt digest"):
            verify_receipt(self.root, receipt)


    def test_execution_entrypoint_does_not_accept_caller_supplied_clock(self):
        with self.assertRaises(TypeError):
            self.execute(now=datetime(2030, 1, 1, tzinfo=timezone.utc))
        self.assertIsNone(self.ledger.state("science-grant-1001"))



if __name__ == "__main__":
    unittest.main()
