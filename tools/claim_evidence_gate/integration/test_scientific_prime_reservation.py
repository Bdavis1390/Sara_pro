"""Integrated signed-verification + local reservation negative tests."""
from __future__ import annotations

import base64
import hashlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_grant_ledger import LocalGrantLedger, LocalGrantLedgerError
from scientific_prime_authorization import (
    ACTION, SCHEMA, SCOPE, ScientificPrimeAuthorizationError,
    canonical_scientific_authorization,
)
from scientific_prime_reservation import verify_and_reserve_science_grant


def b64(raw: bytes):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class PrimeReserveIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.ledger = LocalGrantLedger(self.root / "ledger")
        self.private = Ed25519PrivateKey.generate()
        pub = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.verifier = PrimeSentinelVerifier(public_keys_b64url={"test-key": b64(pub)})
        self.fingerprint = hashlib.sha256(pub).hexdigest()
        config = (ROOT / "examples/bounded_exec/config.json").read_bytes()
        data = (ROOT / "examples/bounded_exec/input.json").read_bytes()
        source = hashlib.sha256((ROOT / "bounded_execution.py").read_bytes()).hexdigest()
        self.now = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.grant = {
            "schema": SCHEMA, "issuer": "PRIME_SENTINEL", "action": ACTION,
            "scope": SCOPE, "key_id": "test-key",
            "authorization_id": "science-auth-1", "nonce": "science-test-nonce-1001",
            "claim_id": "WS-RESERVE-TEST", "prereg_sha256": "c" * 64,
            "run_id": "science-run-1", "config_sha256": hashlib.sha256(config).hexdigest(),
            "input_sha256": hashlib.sha256(data).hexdigest(),
            "executor_sha256": source, "max_samples": 4,
            "issued_at": "2030-01-01T11:59:00Z",
            "expires_at": "2030-01-01T12:08:00Z", "signature_b64url": "",
        }
        self.kwargs = dict(
            ledger=self.ledger, prime_verifier=self.verifier,
            expected_claim_id="WS-RESERVE-TEST", expected_prereg_sha256="c" * 64,
            expected_run_id="science-run-1", expected_config_bytes=config,
            expected_input_bytes=data, expected_executor_sha256=source,
            expected_signer_key_fingerprint_sha256=self.fingerprint, now=self.now,
        )
        self.sign()

    def sign(self):
        self.grant["signature_b64url"] = b64(
            self.private.sign(canonical_scientific_authorization(self.grant))
        )

    def reserve(self, **kwargs):
        arguments = dict(self.kwargs)
        arguments.update(kwargs)
        return verify_and_reserve_science_grant(self.grant, **arguments)

    def test_valid_grant_signature_and_single_reservation(self):
        report = self.reserve()
        self.assertTrue(report["local_reservation_committed"])
        self.assertTrue(report["authorization"]["prime_signature_verified"])
        self.assertFalse(report["execution_performed"])
        self.assertEqual(self.ledger.state("science-auth-1"), "RESERVED")

    def test_duplicate_grant_cannot_reserve_twice(self):
        self.reserve()
        with self.assertRaisesRegex(LocalGrantLedgerError, "already reserved"):
            self.reserve()

    def test_same_grant_cannot_reserve_after_local_reopen(self):
        self.reserve()
        fresh = LocalGrantLedger(self.root / "ledger")
        with self.assertRaisesRegex(LocalGrantLedgerError, "already reserved"):
            self.reserve(ledger=fresh)

    def test_tampered_signature_never_reaches_reservation(self):
        self.grant["signature_b64url"] = "A" * 86
        with self.assertRaisesRegex(ScientificPrimeAuthorizationError, "signature"):
            self.reserve()
        self.assertIsNone(self.ledger.state("science-auth-1"))

    def test_wrong_prereg_pin_never_reaches_reservation(self):
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.reserve(expected_prereg_sha256="0" * 64)
        self.assertIsNone(self.ledger.state("science-auth-1"))

    def test_incorrect_config_bytes_never_reach_reservation(self):
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.reserve(expected_config_bytes=b"modified")
        self.assertIsNone(self.ledger.state("science-auth-1"))

    def test_wrong_trusted_signer_pin_never_reaches_reservation(self):
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.reserve(expected_signer_key_fingerprint_sha256="1" * 64)
        self.assertIsNone(self.ledger.state("science-auth-1"))

    def test_revoked_key_never_reaches_reservation(self):
        pub = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        blocked = PrimeSentinelVerifier(
            public_keys_b64url={"test-key": b64(pub)}, revoked_key_ids={"test-key"}
        )
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.reserve(prime_verifier=blocked)
        self.assertIsNone(self.ledger.state("science-auth-1"))

    def test_expired_grant_never_reaches_reservation(self):
        self.grant["expires_at"] = "2030-01-01T12:00:00Z"
        self.sign()
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.reserve()
        self.assertIsNone(self.ledger.state("science-auth-1"))

    def test_different_action_cannot_be_used_for_science(self):
        self.grant["action"] = "REQUALIFICATION_RELEASE"
        self.sign()
        with self.assertRaises(ScientificPrimeAuthorizationError):
            self.reserve()
        self.assertIsNone(self.ledger.state("science-auth-1"))


if __name__ == "__main__":
    unittest.main()
