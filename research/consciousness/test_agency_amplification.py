import unittest
from agency_amplification import (
    AgencyPath,
    CouplingKind,
    CouplingStage,
    same_frequency_is_not_coupling,
)

class AgencyAmplificationTests(unittest.TestCase):
    def test_external_gain_is_not_energy_creation(self):
        stage = CouplingStage(
            "robotic actuator",
            CouplingKind.BCI,
            input_power_w=0.001,
            output_power_w=10.0,
            externally_powered=True,
            evidence_ref="robot battery",
        )
        self.assertEqual(stage.power_gain(), 10000.0)

    def test_external_power_requires_provenance(self):
        path = AgencyPath(
            "x",
            [CouplingStage(
                "actuator",
                CouplingKind.BCI,
                externally_powered=True,
            )],
        )
        with self.assertRaises(ValueError):
            path.validate()

    def test_frequency_match_without_mechanism_is_not_coupling(self):
        self.assertEqual(
            same_frequency_is_not_coupling(10.0, 10.0, False),
            "NUMERICAL_MATCH_ONLY",
        )

    def test_fully_evidenced_path_gets_higher_ceiling(self):
        path = AgencyPath(
            "bci",
            [
                CouplingStage(
                    "neural measurement",
                    CouplingKind.BCI,
                    evidence_ref="recording",
                ),
                CouplingStage(
                    "robot",
                    CouplingKind.MECHANICAL,
                    externally_powered=True,
                    evidence_ref="powered actuator",
                ),
            ],
        )
        self.assertEqual(
            path.claim_ceiling(),
            "PHYSICALLY_SPECIFIED_CAUSAL_PATHWAY",
        )

if __name__ == "__main__":
    unittest.main()
