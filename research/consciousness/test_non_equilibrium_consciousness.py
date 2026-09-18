import unittest
from non_equilibrium_consciousness import (
    ModelFamily,
    ConsciousnessFeatureVector,
    ModelResult,
    available_features,
    compare_models,
    organized_energy_supported_over_energy_only,
)

class NonEquilibriumConsciousnessTests(unittest.TestCase):
    def test_h0_does_not_include_fdt(self):
        v = ConsciousnessFeatureVector(
            metabolism=1.0,
            total_power=2.0,
            fdt_violation=3.0,
        )
        out = available_features(v, ModelFamily.ENERGY_MAGNITUDE)
        self.assertEqual(set(out), {"metabolism", "total_power"})

    def test_h3_includes_thermodynamic_organization(self):
        v = ConsciousnessFeatureVector(
            metabolism=1.0,
            fdt_violation=2.0,
            entropy_production=3.0,
            dynamical_asymmetry=4.0,
        )
        out = available_features(v, ModelFamily.ORGANIZED_ENERGY)
        self.assertIn("fdt_violation", out)
        self.assertIn("entropy_production", out)

    def test_comparison_is_not_proof_claim(self):
        results = [
            ModelResult(ModelFamily.ENERGY_MAGNITUDE,0.70,0.10,("awake","propofol"),"r1"),
            ModelResult(ModelFamily.ORGANIZED_ENERGY,0.88,0.07,("awake","propofol"),"r2"),
        ]
        out = compare_models(results)
        self.assertEqual(out["best_family"], "H3_ORGANIZED_ENERGY")
        self.assertEqual(out["claim_ceiling"], "COMPARATIVE_MODEL_SUPPORT_ONLY")

    def test_h3_margin_rule(self):
        results = [
            ModelResult(ModelFamily.ENERGY_MAGNITUDE,0.70,0.10,("a",),"r1"),
            ModelResult(ModelFamily.ORGANIZED_ENERGY,0.82,0.08,("a",),"r2"),
        ]
        self.assertTrue(
            organized_energy_supported_over_energy_only(results,0.10)
        )

if __name__ == "__main__":
    unittest.main()
