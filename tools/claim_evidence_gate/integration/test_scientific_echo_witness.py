"""Integration checks against canonical SARA ECHO event/store/checkpoint code.

The key is ephemeral and supplied separately as a *test* trust anchor. These
tests do not establish a third-party witness or independent pinning.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventConflict, EchoEventStore
from worldshepherd_sara.models import AuditRecord

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bounded_execution import run_bounded
from scientific_echo_witness import (
    ScientificEchoWitnessError,
    create_scientific_event,
    verify_scientific_echo_witness,
)

PREREG_PIN = "d" * 64
CLAIM = "WS-TEST-EXECUTION-001"


class ScientificEchoWitnessTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        (self.root / "config.json").write_text('{"operation":"affine_v1","scale":3,"offset":2}\n')
        (self.root / "input.json").write_text('{"samples":[-2,0,1,4]}\n')
        self.receipt = run_bounded(self.root, "config.json", "input.json", "demo")
        self.record = create_scientific_event(
            self.root, self.receipt,
            claim_id=CLAIM, prereg_sha256=PREREG_PIN,
        )

    def checkpoint(self, record=None, key=None, store_name="echo"):
        store = EchoEventStore((self.root / store_name).resolve())
        store.ingest(AuditRecord(**(self.record if record is None else record)))
        private = key or Ed25519PrivateKey.generate()
        manager = EchoCheckpointManager(store, private_key=private, key_id="test-science-echo-key")
        return manager.create_checkpoint(), manager.fingerprint_sha256

    def verify(self, bundle, fingerprint, *, record=None, receipt=None, claim=CLAIM, prereg=PREREG_PIN):
        return verify_scientific_echo_witness(
            self.root,
            self.receipt if receipt is None else receipt,
            self.record if record is None else record,
            bundle,
            expected_claim_id=claim,
            expected_prereg_sha256=prereg,
            expected_checkpoint_key_fingerprint_sha256=fingerprint,
        )

    def test_valid_signed_inclusion_is_proven_with_limited_status(self):
        bundle, fingerprint = self.checkpoint()
        result = self.verify(bundle, fingerprint)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["echo_signed_event_inclusion_verified"])
        self.assertTrue(result["receipt_locally_reproduced"])
        for flag in (
            "prime_authorization_verified", "preexecution_freeze_verified",
            "independent_process_attestation_verified", "third_party_witness_verified",
            "scientific_claim_proven",
        ):
            self.assertIs(result[flag], False)

    def test_wrong_pinned_fingerprint_rejected(self):
        bundle, _ = self.checkpoint()
        with self.assertRaisesRegex(ScientificEchoWitnessError, "checkpoint authentication"):
            self.verify(bundle, "0" * 64)

    def test_signed_checkpoint_tamper_rejected(self):
        bundle, fingerprint = self.checkpoint()
        forged = copy.deepcopy(bundle)
        forged["manifest"]["events"][0]["semantic_sha256"] = "0" * 64
        with self.assertRaises(ScientificEchoWitnessError):
            self.verify(forged, fingerprint)

    def test_bad_checkpoint_signature_rejected(self):
        bundle, fingerprint = self.checkpoint()
        forged = copy.deepcopy(bundle)
        forged["signature_b64url"] = "A" * 86
        with self.assertRaises(ScientificEchoWitnessError):
            self.verify(forged, fingerprint)

    def test_missing_science_event_rejected(self):
        unrelated = create_scientific_event(
            self.root, self.receipt, claim_id="WS-TEST-OTHER", prereg_sha256=PREREG_PIN
        )
        bundle, fingerprint = self.checkpoint(unrelated)
        with self.assertRaisesRegex(ScientificEchoWitnessError, "not uniquely included"):
            self.verify(bundle, fingerprint)

    def test_event_modified_after_checkpoint_rejected(self):
        bundle, fingerprint = self.checkpoint()
        forged = copy.deepcopy(self.record)
        forged["payload"]["output_sha256"] = "0" * 64
        with self.assertRaisesRegex(ScientificEchoWitnessError, "semantic"):
            self.verify(bundle, fingerprint, record=forged)

    def test_actor_impersonation_rejected(self):
        bundle, fingerprint = self.checkpoint()
        forged = copy.deepcopy(self.record)
        forged["actor"] = "ADMIN"
        with self.assertRaisesRegex(ScientificEchoWitnessError, "semantic"):
            self.verify(bundle, fingerprint, record=forged)

    def test_transport_timestamp_can_change_without_semantic_digest_change(self):
        bundle, fingerprint = self.checkpoint()
        changed = copy.deepcopy(self.record)
        changed["timestamp"] = "2026-11-21T09:01:01+00:00"
        self.assertEqual(self.verify(bundle, fingerprint, record=changed)["status"], "PASS")

    def test_wrong_externally_expected_claim_rejected(self):
        bundle, fingerprint = self.checkpoint()
        with self.assertRaisesRegex(ScientificEchoWitnessError, "semantic"):
            self.verify(bundle, fingerprint, claim="WS-ANOTHER-CLAIM")

    def test_wrong_externally_expected_prereg_rejected(self):
        bundle, fingerprint = self.checkpoint()
        with self.assertRaisesRegex(ScientificEchoWitnessError, "semantic"):
            self.verify(bundle, fingerprint, prereg="1" * 64)

    def test_invalid_pinned_prereg_rejected(self):
        bundle, fingerprint = self.checkpoint()
        with self.assertRaises(ScientificEchoWitnessError):
            self.verify(bundle, fingerprint, prereg="not-a-digest")

    def test_modified_receipt_or_input_rejected_before_witness(self):
        bundle, fingerprint = self.checkpoint()
        (self.root / "input.json").write_text('{"samples":[100]}\n')
        with self.assertRaisesRegex(ScientificEchoWitnessError, "not locally reproducible"):
            self.verify(bundle, fingerprint)

    def test_duplicate_event_identity_with_new_semantics_conflicts_in_echo_store(self):
        store = EchoEventStore((self.root / "duplicate-echo").resolve())
        store.ingest(AuditRecord(**self.record))
        modified = copy.deepcopy(self.record)
        modified["payload"]["output_sha256"] = "0" * 64
        with self.assertRaises(EchoEventConflict):
            store.ingest(AuditRecord(**modified))

    def test_untrusted_bundle_key_does_not_match_pinned_identity(self):
        bundle, fingerprint = self.checkpoint()
        different, other_fingerprint = self.checkpoint(store_name="other-echo")
        self.assertNotEqual(fingerprint, other_fingerprint)
        with self.assertRaises(ScientificEchoWitnessError):
            self.verify(different, fingerprint)

    def test_invalid_event_schema_rejected_even_if_self_consistent_and_signed(self):
        altered = copy.deepcopy(self.record)
        altered["payload"]["schema"] = "OTHER-SCHEMA"
        bundle, fingerprint = self.checkpoint(altered)
        with self.assertRaisesRegex(ScientificEchoWitnessError, "semantic"):
            self.verify(bundle, fingerprint, record=altered)

    def test_claimed_prime_verified_flag_not_accepted_even_if_signed(self):
        altered = copy.deepcopy(self.record)
        altered["payload"]["prime_authorization_verified"] = True
        bundle, fingerprint = self.checkpoint(altered)
        with self.assertRaisesRegex(ScientificEchoWitnessError, "semantic"):
            self.verify(bundle, fingerprint, record=altered)

    def test_receipt_cannot_change_without_new_event_identity(self):
        bundle, fingerprint = self.checkpoint()
        changed = copy.deepcopy(self.receipt)
        changed["receipt_sha256"] = "a" * 64
        with self.assertRaisesRegex(ScientificEchoWitnessError, "not locally reproducible"):
            self.verify(bundle, fingerprint, receipt=changed)


if __name__ == "__main__":
    unittest.main()
