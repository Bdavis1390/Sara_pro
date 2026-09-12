from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from prime_gate import evaluate


ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config" / "ws_qphonon_l2_v0_1.json").read_text(encoding="utf-8"))

PASSING_EVIDENCE = {
    "cooperativity_ct2": 1.2,
    "device_temperature_k_mean": 0.100,
    "temperature_violation_probability": 0.005,
    "orbital_leakage_violation_probability": 0.005,
    "parameter_confidence_gates_pass": True,
    "model_holdout_validation_pass": True,
    "claims_state_allows_experiment": True,
    "model_discrepancy_pass": True,
    "mechanical_linewidth_in_envelope": True,
    "detuning_in_envelope": True,
}


class PrimeGateTests(unittest.TestCase):
    def test_passing_evidence_authorizes(self) -> None:
        decision = evaluate(CONFIG, PASSING_EVIDENCE)
        self.assertTrue(decision.authorized)
        self.assertEqual(decision.disposition, "AUTHORIZE_EXPERIMENT")
        self.assertEqual(decision.reasons, [])

    def test_temperature_posterior_risk_blocks(self) -> None:
        evidence = copy.deepcopy(PASSING_EVIDENCE)
        evidence["temperature_violation_probability"] = 0.02
        decision = evaluate(CONFIG, evidence)
        self.assertFalse(decision.authorized)
        self.assertIn("TEMPERATURE_POSTERIOR_RISK_TOO_HIGH", decision.reasons)

    def test_holdout_failure_blocks(self) -> None:
        evidence = copy.deepcopy(PASSING_EVIDENCE)
        evidence["model_holdout_validation_pass"] = False
        decision = evaluate(CONFIG, evidence)
        self.assertFalse(decision.authorized)
        self.assertIn("HOLDOUT_VALIDATION_FAILED", decision.reasons)

    def test_low_cooperativity_blocks(self) -> None:
        evidence = copy.deepcopy(PASSING_EVIDENCE)
        evidence["cooperativity_ct2"] = 0.8
        decision = evaluate(CONFIG, evidence)
        self.assertFalse(decision.authorized)
        self.assertIn("COOPERATIVITY_BELOW_MINIMUM", decision.reasons)

    def test_claims_state_can_block_even_good_physics(self) -> None:
        evidence = copy.deepcopy(PASSING_EVIDENCE)
        evidence["claims_state_allows_experiment"] = False
        decision = evaluate(CONFIG, evidence)
        self.assertFalse(decision.authorized)
        self.assertIn("CLAIMS_STATE_BLOCKS_EXPERIMENT", decision.reasons)


if __name__ == "__main__":
    unittest.main()
