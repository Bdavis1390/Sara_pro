"""Adversarial tests for the separate PRIME scientific grant verifier.

Ephemeral test-only Ed25519 signers. No real authority, private keys, or grants.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scientific_prime_authorization import (
    ACTION, SCHEMA, SCOPE,
    ScientificPrimeAuthorizationError,
    canonical_scientific_authorization,
    verify_scientific_authorization,
)

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
PREREG = "d" * 64
CLAIM = "WS-TEST-EXECUTION-001"
RUN_ID = "run-science-001"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def timestamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


class ScientificPrimeGrantTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        public_bytes = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.fingerprint = hashlib.sha256(public_bytes).hexdigest()
        self.verifier = PrimeSentinelVerifier(public_keys_b64url={"lab-test": b64url(public_bytes)})
        self.config = (ROOT / "examples/bounded_exec/config.json").read_bytes()
        self.data = (ROOT / "examples/bounded_exec/input.json").read_bytes()
        self.source = hashlib.sha256((ROOT / "bounded_execution.py").read_bytes()).hexdigest()
        self.grant = {
            "schema": SCHEMA, "issuer": "PRIME_SENTINEL",
            "action": ACTION, "scope": SCOPE,
            "key_id": "lab-test", "authorization_id": "grant-001",
            "nonce": "science-test-nonce-00001", "claim_id": CLAIM,
            "prereg_sha256": PREREG, "run_id": RUN_ID,
            "config_sha256": hashlib.sha256(self.config).hexdigest(),
            "input_sha256": hashlib.sha256(self.data).hexdigest(),
            "executor_sha256": self.source, "max_samples": 4,
            "issued_at": timestamp(NOW - timedelta(minutes=1)),
            "expires_at": timestamp(NOW + timedelta(minutes=8)),
            "signature_b64url": "",
        }
        self.sign()

    def sign(self):
        self.grant["signature_b64url"] = b64url(
            self.private.sign(canonical_scientific_authorization(self.grant))
        )

    def verify(self, **options):
        args = dict(
            prime_verifier=self.verifier,
            expected_claim_id=CLAIM,
            expected_prereg_sha256=PREREG,
            expected_run_id=RUN_ID,
            expected_config_bytes=self.config,
            expected_input_bytes=self.data,
            expected_executor_sha256=self.source,
            expected_signer_key_fingerprint_sha256=self.fingerprint,
            now=NOW,
        )
        args.update(options)
        return verify_scientific_authorization(self.grant, **args)

    def assert_blocked(self, *text, **options):
        with self.assertRaises(ScientificPrimeAuthorizationError) as error:
            self.verify(**options)
        if text:
            self.assertIn(text[0], str(error.exception))

    def test_valid_signed_bounded_grant(self):
        receipt = self.verify()
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["prime_signature_verified"])
        self.assertEqual(receipt["max_samples"], 4)
        self.assertFalse(receipt["durable_replay_consumption_verified"])
        self.assertFalse(receipt["independent_prereg_freeze_verified"])
        self.assertFalse(receipt["authorized_run_executed"])
        self.assertFalse(receipt["scientific_claim_proven"])

    def test_mutated_claim_rejected_even_if_resigned(self):
        self.grant["claim_id"] = "OTHER"
        self.sign()
        self.assert_blocked("claim, freeze or run binding")

    def test_mutated_configuration_rejected_even_if_resigned(self):
        self.grant["config_sha256"] = "1" * 64
        self.sign()
        self.assert_blocked("configuration bytes not authorized")

    def test_mutated_input_rejected_even_if_resigned(self):
        self.grant["input_sha256"] = "1" * 64
        self.sign()
        self.assert_blocked("input bytes not authorized")

    def test_mutated_executor_rejected_even_if_resigned(self):
        self.grant["executor_sha256"] = "1" * 64
        self.sign()
        self.assert_blocked("executor source not authorized")

    def test_wrong_expected_preregistration_rejected(self):
        self.assert_blocked("claim, freeze or run binding", expected_prereg_sha256="1" * 64)

    def test_wrong_expected_run_rejected(self):
        self.assert_blocked("claim, freeze or run binding", expected_run_id="other-run")

    def test_wrong_key_pin_rejected_even_for_valid_signature(self):
        self.assert_blocked("not independently pinned", expected_signer_key_fingerprint_sha256="0" * 64)

    def test_revoked_key_rejected(self):
        self.assert_blocked("PRIME signature rejected", prime_verifier=PrimeSentinelVerifier(
            public_keys_b64url={"lab-test": b64url(self.private.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            ))},
            revoked_key_ids={"lab-test"},
        ))

    def test_unknown_key_rejected(self):
        self.assert_blocked("PRIME signature rejected", prime_verifier=PrimeSentinelVerifier(
            public_keys_b64url={}
        ))

    def test_signature_tamper_rejected(self):
        self.grant["signature_b64url"] = "A" * 86
        self.assert_blocked("PRIME signature rejected")

    def test_requalification_release_not_scientific_authorization(self):
        self.grant["action"] = "REQUALIFICATION_RELEASE"
        self.sign()
        self.assert_blocked("action not allowed")

    def test_other_operation_scope_rejected(self):
        self.grant["scope"] = "GENERAL_SHELL_EXECUTION"
        self.sign()
        self.assert_blocked("scope not allowed")

    def test_expired_grant_rejected(self):
        self.grant["expires_at"] = timestamp(NOW)
        self.sign()
        self.assert_blocked("not currently valid")

    def test_overlong_lifetime_rejected(self):
        self.grant["expires_at"] = timestamp(NOW + timedelta(minutes=16))
        self.sign()
        self.assert_blocked("duration invalid")

    def test_future_dated_grant_rejected(self):
        self.grant["issued_at"] = timestamp(NOW + timedelta(minutes=2))
        self.grant["expires_at"] = timestamp(NOW + timedelta(minutes=4))
        self.sign()
        self.assert_blocked("not currently valid")

    def test_budget_overrun_rejected(self):
        self.grant["max_samples"] = 2
        self.sign()
        self.assert_blocked("sample budget")

    def test_bool_budget_rejected(self):
        self.grant["max_samples"] = True
        self.sign()
        self.assert_blocked("max_samples")

    def test_unlimited_budget_rejected(self):
        self.grant["max_samples"] = 1000
        self.sign()
        self.assert_blocked("max_samples")

    def test_extra_field_rejected(self):
        self.grant["shell"] = "sh -c arbitrary"
        self.assert_blocked("shape mismatch")

    def test_consumed_id_rejected(self):
        self.assert_blocked("authorization already consumed", consumed_authorization_ids={"grant-001"})

    def test_consumed_nonce_rejected(self):
        self.assert_blocked("nonce already consumed", consumed_nonces={"science-test-nonce-00001"})

    def test_altered_bytes_rejected_without_grant_edit(self):
        self.assert_blocked("configuration bytes not authorized",
                            expected_config_bytes=b'{"operation":"affine_v1","scale":9,"offset":0}')

    def test_invalid_signature_does_not_become_valid_on_other_key(self):
        other = Ed25519PrivateKey.generate()
        foreign_pub = other.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        self.assert_blocked("PRIME signature rejected", prime_verifier=PrimeSentinelVerifier(
            public_keys_b64url={"lab-test": b64url(foreign_pub)}
        ))

    def test_invalid_issued_at_timezone_rejected(self):
        self.grant["issued_at"] = "2030-01-01T11:00:00"
        self.sign()
        self.assert_blocked("issued_at must be UTC")

    def test_bad_nonce_rejected(self):
        self.grant["nonce"] = "short"
        self.sign()
        self.assert_blocked("invalid nonce")


if __name__ == "__main__":
    unittest.main()
