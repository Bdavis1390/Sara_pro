import unittest
from epistemic_action import (
    HypothesisDistribution,
    OutcomePosterior,
    CandidateAction,
    expected_information_gain_bits,
    bounded_epistemic_utility,
    choose_action,
)

class EpistemicActionTests(unittest.TestCase):
    def setUp(self):
        self.prior = HypothesisDistribution({"H1":0.5,"H2":0.5})

    def test_perfect_discriminator_gives_one_bit(self):
        action = CandidateAction(
            "test",
            (
                OutcomePosterior(0.5,HypothesisDistribution({"H1":1.0,"H2":0.0})),
                OutcomePosterior(0.5,HypothesisDistribution({"H1":0.0,"H2":1.0})),
            ),
            risk=0.0,cost=0.0,irreversibility=0.0,
        )
        self.assertAlmostEqual(
            expected_information_gain_bits(self.prior, action),1.0
        )

    def test_uninformative_action_gives_zero(self):
        action = CandidateAction(
            "repeat",
            (
                OutcomePosterior(1.0,self.prior),
            ),
            risk=0.0,cost=0.0,irreversibility=0.0,
        )
        self.assertAlmostEqual(
            expected_information_gain_bits(self.prior, action),0.0
        )

    def test_unauthorized_action_is_never_selected_on_information_alone(self):
        action = CandidateAction(
            "forbidden",
            (OutcomePosterior(1.0,self.prior),),
            risk=0,cost=0,irreversibility=0,
            authorized=False,
        )
        self.assertEqual(
            bounded_epistemic_utility(self.prior,action),
            float("-inf"),
        )

    def test_safer_useful_action_can_beat_risky_perfect_test(self):
        perfect_risky = CandidateAction(
            "risky",
            (
                OutcomePosterior(0.5,HypothesisDistribution({"H1":1.0,"H2":0.0})),
                OutcomePosterior(0.5,HypothesisDistribution({"H1":0.0,"H2":1.0})),
            ),
            risk=2.0,cost=0,irreversibility=1.0,
        )
        partial_safe = CandidateAction(
            "safe",
            (
                OutcomePosterior(0.5,HypothesisDistribution({"H1":0.8,"H2":0.2})),
                OutcomePosterior(0.5,HypothesisDistribution({"H1":0.2,"H2":0.8})),
            ),
            risk=0.0,cost=0.1,irreversibility=0.0,
        )
        name,_ = choose_action(self.prior,[perfect_risky,partial_safe])
        self.assertEqual(name,"safe")

if __name__ == "__main__":
    unittest.main()
