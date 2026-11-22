"""End-to-end *synthetic* PRIME -> reservation -> execution -> ECHO custody tests.

All keys are ephemeral test-only keys. A signed checkpoint can authenticate event
inclusion but never establish independent physical measurement or key custody.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from authorized_synthetic_execution import execute_authorized_synthetic
from bounded_execution import receipt_digest, verify_receipt
from local_grant_ledger import LocalGrantLedger
from scientific_echo_witness import (
    ScientificEchoWitnessError, create_scientific_event, verify_scientific_echo_witness,
)
from scientific_prime_authorization import ACTION, SCHEMA, SCOPE, canonical_scientific_authorization

CLAIM = "WS-SYNTHETIC-CHAIN-001"
PREREG_PIN = "c" * 64


def encoded(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def timestamp(t: datetime) -> str:
    return t.isoformat(timespec="seconds").replace("+00:00", "Z")


class AuthorizedEchoRoundtripTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        for item in ("config.json", "input.json"):
            shutil.copy(ROOT / "examples/bounded_exec" / item, self.root / item)
        self.ledger = LocalGrantLedger(self.root / "ledger")
        self.prime = Ed25519PrivateKey.generate()
        prime_public = self.prime.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        self.prime_verifier = PrimeSentinelVerifier(
            public_keys_b64url={"prime-test-science": encoded(prime_public)}
        )
        self.prime_pin = hashlib.sha256(prime_public).hexdigest()
        now = datetime.now(timezone.utc)
        grant = {
            "schema": SCHEMA, "issuer": "PRIME_SENTINEL",
            "action": ACTION, "scope": SCOPE,
            "key_id": "prime-test-science",
            "authorization_id": "auth-chain-001",
            "nonce": "science-echo-test-nonce-1",
            "claim_id": CLAIM, "prereg_sha256": PREREG_PIN, "run_id": "echo-run-001",
            "config_sha256": hashlib.sha256((self.root / "config.json").read_bytes()).hexdigest(),
            "input_sha256": hashlib.sha256((self.root / "input.json").read_bytes()).hexdigest(),
            "executor_sha256": hashlib.sha256((ROOT / "bounded_execution.py").read_bytes()).hexdigest(),
            "max_samples": 4,
            "issued_at": timestamp(now - timedelta(seconds=20)),
            "expires_at": timestamp(now + timedelta(minutes=5)),
            "signature_b64url": "",
        }
        grant["signature_b64url"] = encoded(self.prime.sign(canonical_scientific_authorization(grant)))
        self.run = execute_authorized_synthetic(
            self.root, grant, config_path="config.json", input_path="input.json",
            ledger=self.ledger, prime_verifier=self.prime_verifier,
            expected_claim_id=CLAIM, expected_prereg_sha256=PREREG_PIN,
            expected_signer_key_fingerprint_sha256=self.prime_pin,
        )
        self.assertEqual(self.ledger.state("auth-chain-001"), "FINISHED")
        self.record = create_scientific_event(
            self.root, self.run["receipt"], claim_id=CLAIM, prereg_sha256=PREREG_PIN
        )
        self.store = EchoEventStore((self.root / "echo").resolve())
        self.store.ingest(AuditRecord(**self.record))
        self.manager = EchoCheckpointManager(
            self.store, private_key=Ed25519PrivateKey.generate(), key_id="echo-test-science"
        )

    def verify(self, chain, receipt=None, record=None):
        return verify_scientific_echo_witness(
            self.root, self.run["receipt"] if receipt is None else receipt,
            self.record if record is None else record, chain,
            expected_claim_id=CLAIM, expected_prereg_sha256=PREREG_PIN,
            expected_checkpoint_key_fingerprint_sha256=self.manager.fingerprint_sha256,
        )

    def test_authorized_execution_can_be_reproduced_and_signed_as_event(self):
        chain = [self.manager.create_checkpoint()]
        report = self.verify(chain)
        self.assertTrue(self.run["prime_signature_verified_for_this_run"])
        self.assertTrue(report["echo_signed_event_inclusion_verified"])
        self.assertTrue(report["echo_signed_checkpoint_chain_verified"])
        self.assertTrue(report["receipt_locally_reproduced"])
        self.assertEqual(report["checkpoint_count"], 1)
        self.assertIs(report["prime_authorization_verified"], False)
        self.assertIs(report["scientific_claim_proven"], False)
        self.assertIs(report["third_party_witness_verified"], False)

    def test_authorized_run_attested_across_two_local_checkpoints(self):
        first = self.manager.create_checkpoint()
        second_record = create_scientific_event(
            self.root, self.run["receipt"],
            claim_id="WS-SYNTHETIC-CHAIN-OTHER", prereg_sha256=PREREG_PIN,
        )
        self.store.ingest(AuditRecord(**second_record))
        second = self.manager.create_checkpoint()
        report = self.verify([first, second])
        self.assertEqual(report["checkpoint_count"], 2)
        with self.assertRaises(ScientificEchoWitnessError):
            self.verify([second])

    def test_signed_event_cannot_hide_output_change_after_execution(self):
        chain = [self.manager.create_checkpoint()]
        (self.root / "runs/echo-run-001.output.json").write_text('{"samples":[999]}\n')
        with self.assertRaisesRegex(ScientificEchoWitnessError, "not locally reproducible"):
            self.verify(chain)

    def test_rehashed_modified_local_authorization_receipt_is_not_same_signed_event(self):
        chain = [self.manager.create_checkpoint()]
        receipt = copy.deepcopy(self.run["receipt"])
        receipt["authorization"]["grant_sha256"] = "0" * 64
        receipt["receipt_sha256"] = receipt_digest({
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        })
        self.assertEqual(verify_receipt(self.root, receipt)["status"], "PASS")
        with self.assertRaisesRegex(ScientificEchoWitnessError, "semantic"):
            self.verify(chain, receipt=receipt)


if __name__ == "__main__":
    unittest.main()
