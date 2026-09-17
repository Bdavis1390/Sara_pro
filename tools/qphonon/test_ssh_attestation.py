from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from security_controls import canonical_json_bytes
from ssh_attestation import NAMESPACE, approval_payload, verify_approval_signature


APPROVAL = {
    "approved": True,
    "approval_id": "123e4567-e89b-42d3-b456-426614174555",
    "approver": "test-human",
    "experiment_digest": "1" * 64,
    "config_digest": "2" * 64,
    "issued_at_utc": "2026-09-17T23:00:00Z",
    "expires_at_utc": "2026-09-17T23:10:00Z",
}


@unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is required")
class SSHAttestationTests(unittest.TestCase):
    def _fixture(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        key = root / "id_ed25519"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
            check=True,
        )
        pub = (root / "id_ed25519.pub").read_text(encoding="utf-8").strip().split()
        signers = root / "allowed_signers"
        signers.write_text(f"test-human {pub[0]} {pub[1]}\n", encoding="utf-8")

        payload_file = root / "approval.payload"
        payload_file.write_bytes(canonical_json_bytes(approval_payload(APPROVAL)))
        subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(payload_file)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        signature = Path(str(payload_file) + ".sig")
        return tmp, signers, signature

    def test_valid_ed25519_attestation_verifies(self) -> None:
        tmp, signers, signature = self._fixture()
        try:
            decision = verify_approval_signature(
                APPROVAL,
                signature_path=signature,
                allowed_signers_path=signers,
                principal="test-human",
            )
            self.assertTrue(decision.verified, decision.reason)
        finally:
            tmp.cleanup()

    def test_payload_tamper_breaks_signature(self) -> None:
        tmp, signers, signature = self._fixture()
        try:
            changed = dict(APPROVAL)
            changed["experiment_digest"] = "9" * 64
            decision = verify_approval_signature(
                changed,
                signature_path=signature,
                allowed_signers_path=signers,
                principal="test-human",
            )
            self.assertFalse(decision.verified)
            self.assertEqual(decision.reason, "SIGNATURE_VERIFICATION_FAILED")
        finally:
            tmp.cleanup()

    def test_wrong_principal_fails(self) -> None:
        tmp, signers, signature = self._fixture()
        try:
            decision = verify_approval_signature(
                APPROVAL,
                signature_path=signature,
                allowed_signers_path=signers,
                principal="someone-else",
            )
            self.assertFalse(decision.verified)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
