"""Persistent local replay-control tests using an ephemeral PRIME test signing key."""
from __future__ import annotations

import base64
import copy
import hashlib
import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_grant_ledger import LocalGrantLedger, LocalGrantLedgerError
from scientific_prime_authorization import (
    ACTION, SCHEMA, SCOPE,
    canonical_scientific_authorization, verify_scientific_authorization,
)


def encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class LocalGrantLedgerTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.location = self.root / "private-ledger"
        self.signer = Ed25519PrivateKey.generate()
        pub = self.signer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.verifier = PrimeSentinelVerifier(public_keys_b64url={"test-prime": encode(pub)})
        self.fingerprint = hashlib.sha256(pub).hexdigest()
        self.config = (ROOT / "examples/bounded_exec/config.json").read_bytes()
        self.inputs = (ROOT / "examples/bounded_exec/input.json").read_bytes()
        self.source = hashlib.sha256((ROOT / "bounded_execution.py").read_bytes()).hexdigest()
        self.at = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
        assertion = {
            "schema": SCHEMA, "issuer": "PRIME_SENTINEL", "action": ACTION,
            "scope": SCOPE, "key_id": "test-prime",
            "authorization_id": "auth-001", "nonce": "nonce-science-test-001",
            "claim_id": "WS-CLAIM-1", "prereg_sha256": "a" * 64,
            "run_id": "test-run", "config_sha256": hashlib.sha256(self.config).hexdigest(),
            "input_sha256": hashlib.sha256(self.inputs).hexdigest(),
            "executor_sha256": self.source, "max_samples": 4,
            "issued_at": "2030-01-01T11:59:00Z",
            "expires_at": "2030-01-01T12:09:00Z",
            "signature_b64url": "",
        }
        assertion["signature_b64url"] = encode(
            self.signer.sign(canonical_scientific_authorization(assertion))
        )
        self.verified = verify_scientific_authorization(
            assertion, prime_verifier=self.verifier,
            expected_claim_id="WS-CLAIM-1", expected_prereg_sha256="a" * 64,
            expected_run_id="test-run", expected_config_bytes=self.config,
            expected_input_bytes=self.inputs,
            expected_executor_sha256=self.source,
            expected_signer_key_fingerprint_sha256=self.fingerprint,
            now=self.at,
        )

    def ledger(self):
        return LocalGrantLedger(self.location)

    def test_valid_verified_grant_is_reserved(self):
        gate = self.ledger()
        result = gate.reserve(self.verified)
        self.assertEqual(result["state"], "RESERVED")
        self.assertFalse(result["distributed_replay_protected"])
        self.assertFalse(result["execution_performed"])
        self.assertEqual(gate.state("auth-001"), "RESERVED")

    def test_reservation_stays_after_process_like_reopen(self):
        self.ledger().reserve(self.verified)
        with self.assertRaisesRegex(LocalGrantLedgerError, "already reserved"):
            self.ledger().reserve(self.verified)

    def test_reused_nonce_with_different_id_rejected(self):
        gate = self.ledger()
        gate.reserve(self.verified)
        modified = copy.deepcopy(self.verified)
        modified["authorization_id"] = "auth-002"
        with self.assertRaisesRegex(LocalGrantLedgerError, "already reserved"):
            gate.reserve(modified)

    def test_reused_id_with_new_nonce_rejected(self):
        gate = self.ledger()
        gate.reserve(self.verified)
        modified = copy.deepcopy(self.verified)
        modified["nonce"] = "another-science-nonce-003"
        with self.assertRaisesRegex(LocalGrantLedgerError, "already reserved"):
            gate.reserve(modified)

    def test_completed_reservation_remains_consumed(self):
        gate = self.ledger()
        gate.reserve(self.verified)
        gate.mark_finished("auth-001")
        self.assertEqual(gate.state("auth-001"), "FINISHED")
        with self.assertRaisesRegex(LocalGrantLedgerError, "already reserved"):
            gate.reserve(self.verified)

    def test_double_completion_is_not_silent(self):
        gate = self.ledger()
        gate.reserve(self.verified)
        gate.mark_finished("auth-001")
        with self.assertRaisesRegex(LocalGrantLedgerError, "already finished"):
            gate.mark_finished("auth-001")

    def test_missing_completion_is_rejected(self):
        with self.assertRaisesRegex(LocalGrantLedgerError, "missing"):
            self.ledger().mark_finished("auth-missing")

    def test_bad_verification_status_rejected(self):
        changed = copy.deepcopy(self.verified)
        changed["status"] = "FAKE"
        with self.assertRaisesRegex(LocalGrantLedgerError, "untrusted"):
            self.ledger().reserve(changed)

    def test_forged_unsigned_auth_verification_flag_rejected(self):
        changed = copy.deepcopy(self.verified)
        changed["prime_signature_verified"] = False
        with self.assertRaisesRegex(LocalGrantLedgerError, "untrusted"):
            self.ledger().reserve(changed)

    def test_invalid_id_does_not_enter_database(self):
        changed = copy.deepcopy(self.verified)
        changed["authorization_id"] = "'; DROP TABLE reservation;--"
        with self.assertRaisesRegex(LocalGrantLedgerError, "invalid authorization_id"):
            self.ledger().reserve(changed)

    def test_private_file_permissions(self):
        gate = self.ledger()
        self.assertEqual(stat.S_IMODE(self.location.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(gate.db_path.stat().st_mode), 0o600)

    def test_insecure_existing_directory_rejected(self):
        self.location.mkdir(mode=0o700)
        self.location.chmod(0o755)
        with self.assertRaisesRegex(LocalGrantLedgerError, "permissions too broad"):
            self.ledger()

    def test_symlinked_directory_rejected(self):
        (self.root / "actual").mkdir()
        self.location.symlink_to(self.root / "actual")
        with self.assertRaisesRegex(LocalGrantLedgerError, "symlink"):
            self.ledger()

    def test_symlinked_database_rejected(self):
        self.location.mkdir(mode=0o700)
        (self.location / "science-grants.db").symlink_to(self.root / "outside")
        with self.assertRaisesRegex(LocalGrantLedgerError, "symlink"):
            self.ledger()

    def test_corrupt_schema_is_rejected(self):
        self.ledger()
        conn = sqlite3.connect(self.location / "science-grants.db")
        conn.execute("UPDATE metadata SET value='OTHER' WHERE name='schema'")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(LocalGrantLedgerError, "schema mismatch"):
            self.ledger()

    def test_concurrent_reservation_has_single_winner(self):
        self.ledger()
        def claim(_):
            try:
                self.ledger().reserve(self.verified)
                return True
            except LocalGrantLedgerError:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(claim, range(4)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 3)

    def test_different_legitimate_grants_can_be_separately_reserved(self):
        gate = self.ledger()
        gate.reserve(self.verified)
        other = copy.deepcopy(self.verified)
        other["authorization_id"] = "auth-002"
        other["nonce"] = "another-science-nonce-003"
        other["run_id"] = "run-002"
        gate.reserve(other)
        self.assertEqual(gate.state("auth-002"), "RESERVED")

    def test_reservation_does_not_create_experiment_results(self):
        gate = self.ledger()
        gate.reserve(self.verified)
        self.assertFalse((self.location / "runs").exists())


if __name__ == "__main__":
    unittest.main()
