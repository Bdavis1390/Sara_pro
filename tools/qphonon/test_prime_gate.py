from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from prime_gate import evaluate
from registry_adapter import build_record


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

SYNTHETIC_PARAMETERS = {
    "g1_hz": 3_000_000.0,
    "g2_hz": 2_950_000.0,
    "kappa_m_hz": 350_000.0,
    "gamma_eff_hz": 420_000.0,
    "t2_s": 5.0e-6,
    "t1_s": 100.0e-6,
    "detuning_hz": 50_000.0,
    "device_temperature_k": 0.100,
    "thermal_occupation": 0.0032,
    "acoustic_drive_hz": 76_000_000.0,
    "orbital_leakage_probability": 5.0e-4,
    "transducer_response": {"status": "synthetic_test_fixture"},
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

    def test_synthetic_registry_to_prime_nominal_path(self) -> None:
        record = build_record(
            CONFIG,
            SYNTHETIC_PARAMETERS,
            {"source": "synthetic_ci_fixture", "physical_hardware": False},
        )
        self.assertTrue(record.complete)
        self.assertEqual(record.claims_state, "ARCHITECTURE_INTEGRATED_PHYSICAL_CAPABILITY_NOT_CLAIMED")
        self.assertFalse(record.provenance["physical_hardware"])

        decision = evaluate(CONFIG, PASSING_EVIDENCE)
        self.assertTrue(decision.authorized)
        self.assertEqual(decision.disposition, "AUTHORIZE_EXPERIMENT")

    def test_synthetic_drifted_case_fails_safe(self) -> None:
        record = build_record(
            CONFIG,
            SYNTHETIC_PARAMETERS,
            {"source": "synthetic_ci_fixture", "physical_hardware": False},
        )
        self.assertTrue(record.complete)

        evidence = copy.deepcopy(PASSING_EVIDENCE)
        evidence.update(
            {
                "device_temperature_k_mean": 0.135,
                "temperature_violation_probability": 0.30,
                "mechanical_linewidth_in_envelope": False,
                "detuning_in_envelope": False,
                "model_discrepancy_pass": False,
            }
        )
        decision = evaluate(CONFIG, evidence)
        self.assertFalse(decision.authorized)
        self.assertEqual(decision.disposition, "CHARACTERIZE_OR_ABORT")
        self.assertIn("TEMPERATURE_MEAN_ABOVE_SCREEN", decision.reasons)
        self.assertIn("TEMPERATURE_POSTERIOR_RISK_TOO_HIGH", decision.reasons)
        self.assertIn("MECHANICAL_LINEWIDTH_OUT_OF_ENVELOPE", decision.reasons)
        self.assertIn("DETUNING_OUT_OF_ENVELOPE", decision.reasons)
        self.assertIn("MODEL_DISCREPANCY_OUT_OF_BOUNDS", decision.reasons)


if __name__ == "__main__":
    unittest.main()
