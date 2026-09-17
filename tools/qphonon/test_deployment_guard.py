from __future__ import annotations

from argparse import Namespace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid

from deployment_guard import verify_and_commit_event, verify_and_consume_approval
from security_controls import compute_event_digest, canonical_json_bytes
from ssh_attestation import NAMESPACE, approval_payload


@unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is required")
class DeploymentGuardIntegrationTests(unittest.TestCase):
    def test_signed_approval_is_consumed_once_across_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_db = root / "state.sqlite3"
            key = root / "id_ed25519"
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                check=True,
            )
            pub = (root / "id_ed25519.pub").read_text(encoding="utf-8").strip().split()
            signers = root / "allowed_signers"
            signers.write_text(f"test-human {pub[0]} {pub[1]}\n", encoding="utf-8")

            now = datetime.now(timezone.utc)
            approval = {
                "approved": True,
                "approval_id": str(uuid.uuid4()),
                "approver": "test-human",
                "experiment_digest": "1" * 64,
                "config_digest": "2" * 64,
                "issued_at_utc": (now - timedelta(seconds=5)).isoformat().replace("+00:00", "Z"),
                "expires_at_utc": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            }
            approval_path = root / "approval.json"
            approval_path.write_text(json.dumps(approval), encoding="utf-8")

            payload_file = root / "approval.payload"
            payload_file.write_bytes(canonical_json_bytes(approval_payload(approval)))
            subprocess.run(
                ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(payload_file)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            signature = Path(str(payload_file) + ".sig")

            prime = {
                "authorized": True,
                "disposition": "READY_FOR_HUMAN_APPROVAL",
                "reasons": [],
                "requires_human_approval": True,
            }
            prime_path = root / "prime.json"
            prime_path.write_text(json.dumps(prime), encoding="utf-8")

            args = Namespace(
                approval=str(approval_path),
                prime_decision=str(prime_path),
                state_db=str(state_db),
                signature=str(signature),
                allowed_signers=str(signers),
                principal="test-human",
                experiment_digest="1" * 64,
                config_digest="2" * 64,
            )
            code, output = verify_and_consume_approval(args)
            self.assertEqual(code, 0, output)
            self.assertEqual(output["disposition"], "EXECUTION_ALLOWED")

            code, output = verify_and_consume_approval(args)
            self.assertEqual(code, 2)
            self.assertIn("APPROVAL_REPLAY_DETECTED", output["reasons"])

    def test_event_chain_commits_then_rejects_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event = {
                "schema": "WS-QPHONON-ECHO-EVENT-V0.2",
                "event_id": str(uuid.uuid4()),
                "event_sequence": 0,
                "event_time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "raw_data_hash": "c" * 64,
                "config_digest": "a" * 64,
                "previous_event_digest": "0" * 64,
                "event_digest": "0" * 64,
                "model_version": "deployment-test",
                "prior": {},
                "posterior": {},
                "experiment_proposed": {"kind": "synthetic"},
                "expected_information_gain": 0.0,
                "prime_decision": {
                    "authorized": False,
                    "disposition": "CHARACTERIZE_OR_ABORT",
                    "reasons": ["TEST"],
                    "requires_human_approval": False,
                },
                "control_waveform_or_parameters": {},
                "environmental_state": {"physical_hardware": False},
                "measurement_result": {},
                "model_discrepancy": {},
                "claims_state": "SIMULATED_ONLY",
            }
            event["event_digest"] = compute_event_digest(event)
            event_path = root / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")

            args = Namespace(
                event=str(event_path),
                state_db=str(root / "state.sqlite3"),
                stream="synthetic-lab",
                config_digest="a" * 64,
            )
            code, output = verify_and_commit_event(args)
            self.assertEqual(code, 0, output)
            self.assertEqual(output["disposition"], "EVIDENCE_COMMITTED")

            code, output = verify_and_commit_event(args)
            self.assertEqual(code, 2)
            self.assertEqual(output["disposition"], "REJECT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
