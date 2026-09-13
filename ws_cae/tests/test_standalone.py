import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ws_cae.cli import InputError, parse_profile, run
from ws_cae.policy import Policy, evaluate
from ws_cae.reference import Profile, assess


class StandaloneTests(unittest.TestCase):
    def algorand(self, **overrides):
        data = dict(
            ecosystem="Algorand", adapter_class="NATIVE_REKEY", implementation_maturity="MAINNET",
            stable_authority_id=True, authenticator_replaceable=True, pq_authorization_state="PQ_MAINNET",
            policy_state_documented=True, recovery_state_documented=True, domain_binding_documented=True,
            evidence_state_documented=True, consensus_pq_state="CLASSICAL_OR_UNPROVEN",
        )
        data.update(overrides)
        return Profile(**data)

    def write(self, payload):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(payload, handle)
        return Path(handle.name)

    def test_account_authority_does_not_imply_pq_consensus(self):
        result = assess(self.algorand())
        self.assertTrue(result.valid)
        self.assertEqual(result.consensus_boundary, "ACCOUNT_AUTHORITY_RESULT_DOES_NOT_ESTABLISH_PQ_CONSENSUS")

    def test_utxo_style_limited_mainnet_path_is_representable_without_stable_identity(self):
        profile = self.algorand(
            ecosystem="UTXO-reference",
            adapter_class="UTXO_HASH_PREPOSITIONING",
            stable_authority_id=False,
            authenticator_replaceable=False,
            pq_authorization_state="PQ_MAINNET_LIMITED",
            policy_state_documented=False,
            recovery_state_documented=False,
        )
        result = assess(profile)
        self.assertTrue(result.valid)
        self.assertEqual(result.authority_state, "AUTHORITY_ABSTRACTION_NOT_ESTABLISHED")
        self.assertEqual(result.pq_authorization_state, "PQ_MAINNET_LIMITED")

    def test_consumer_policy_is_independent_of_chain_profile(self):
        profile = self.algorand()
        strict = Policy(
            name="strict", minimum_maturity="MAINNET", accepted_pq_authorization_states=("PQ_MAINNET",),
            require_stable_authority_id=True, require_authenticator_replaceable=True,
            require_policy_state_documented=True, require_recovery_state_documented=True,
        )
        self.assertTrue(evaluate(profile, assess(profile), strict).passed)
        ethereum = self.algorand(ecosystem="Ethereum", implementation_maturity="DEVNET", pq_authorization_state="PLUGGABLE_AUTH_ONLY")
        self.assertFalse(evaluate(ethereum, assess(ethereum), strict).passed)

    def test_unknown_profile_fields_fail_closed(self):
        raw = self.algorand().__dict__ | {"invented_claim": True}
        with self.assertRaises(InputError):
            parse_profile(raw)

    def test_reference_batch_and_interop_policy_pass(self):
        result = run(ROOT / "ws_cae/examples/reference_pair.json", ROOT / "ws_cae/examples/interop_policy.json")
        self.assertTrue(result["all_valid"])
        self.assertTrue(result["all_policy_pass"])

    def test_institutional_policy_distinguishes_algorand_and_ethereum(self):
        result = run(ROOT / "ws_cae/examples/reference_pair.json", ROOT / "ws_cae/examples/institutional_policy.json")
        self.assertTrue(result["all_valid"])
        self.assertFalse(result["all_policy_pass"])
        by_name = {x["ecosystem"]: x for x in result["results"]}
        self.assertTrue(by_name["Algorand"]["policy"]["passed"])
        self.assertFalse(by_name["Ethereum"]["policy"]["passed"])

    def test_cli_exit_codes(self):
        cmd = [sys.executable, "-m", "ws_cae.cli", "ws_cae/examples/reference_pair.json", "--policy", "ws_cae/examples/interop_policy.json"]
        good = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(good.returncode, 0)
        bad = subprocess.run(
            [sys.executable, "-m", "ws_cae.cli", "ws_cae/examples/reference_pair.json", "--policy", "ws_cae/examples/institutional_policy.json"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(bad.returncode, 1)


if __name__ == "__main__":
    unittest.main()
