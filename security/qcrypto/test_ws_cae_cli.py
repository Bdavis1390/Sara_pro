import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ws_cae_cli import ProfileInputError, assess_path, parse_profile


class WSCAECLITests(unittest.TestCase):
    def valid_profile(self, **overrides):
        profile = {
            "ecosystem": "Algorand",
            "adapter_class": "NATIVE_REKEY",
            "implementation_maturity": "MAINNET",
            "stable_authority_id": True,
            "authenticator_replaceable": True,
            "pq_authorization_state": "PQ_MAINNET",
            "policy_state_documented": True,
            "recovery_state_documented": True,
            "domain_binding_documented": True,
            "evidence_state_documented": True,
            "consensus_pq_state": "CLASSICAL_OR_UNPROVEN",
        }
        profile.update(overrides)
        return profile

    def write_json(self, payload):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(payload, handle)
        return Path(handle.name)

    def test_valid_profile_assesses_cleanly(self):
        path = self.write_json(self.valid_profile())
        result = assess_path(path)
        self.assertTrue(result["all_valid"])
        self.assertEqual(result["profile_count"], 1)
        self.assertEqual(result["results"][0]["assessment"]["maturity_state"], "IMPLEMENTATION_MAINNET")

    def test_batch_preserves_maturity_boundaries(self):
        path = self.write_json(
            {
                "profiles": [
                    self.valid_profile(),
                    self.valid_profile(
                        ecosystem="Ethereum",
                        adapter_class="NATIVE_ACCOUNT_ABSTRACTION",
                        implementation_maturity="DEVNET",
                        pq_authorization_state="PLUGGABLE_AUTH_ONLY",
                    ),
                ]
            }
        )
        result = assess_path(path)
        self.assertTrue(result["all_valid"])
        states = [item["assessment"]["maturity_state"] for item in result["results"]]
        self.assertEqual(states, ["IMPLEMENTATION_MAINNET", "IMPLEMENTATION_DEVNET"])

    def test_unknown_fields_fail_closed(self):
        profile = self.valid_profile(extra_claim=True)
        with self.assertRaises(ProfileInputError):
            parse_profile(profile)

    def test_missing_binding_produces_nonconformant_exit(self):
        path = self.write_json(self.valid_profile(domain_binding_documented=False))
        cli = Path(__file__).with_name("ws_cae_cli.py")
        completed = subprocess.run(
            [sys.executable, str(cli), str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 1)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["all_valid"])

    def test_malformed_input_uses_exit_code_two(self):
        path = self.write_json({"ecosystem": "Incomplete"})
        cli = Path(__file__).with_name("ws_cae_cli.py")
        completed = subprocess.run(
            [sys.executable, str(cli), str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertIn("input_error", payload)


if __name__ == "__main__":
    unittest.main()
