import unittest
from textual_topology import (
    TextUnit,
    OrderConstraint,
    ordinal_constraints,
    infer_order_exhaustive,
    validate_against_witness,
)

class TextualTopologyTests(unittest.TestCase):
    def test_ordinals_recover_dislocated_order(self):
        units = [
            TextUnit("week8", 8, "w8", 0),
            TextUnit("week1", 1, "w1", 1),
            TextUnit("week2", 2, "w2", 2),
            TextUnit("week3", 3, "w3", 3),
        ]
        result = infer_order_exhaustive(
            units,
            ordinal_constraints(units),
        )
        self.assertEqual(
            result["order"],
            ["week1","week2","week3","week8"],
        )

    def test_independent_witness_validation(self):
        result = validate_against_witness(
            ["w1","w2","w3","w4"],
            ["w1","w2","w3","w4"],
        )
        self.assertTrue(result["exact_on_common_units"])
        self.assertEqual(
            result["claim_state"],
            "INDEPENDENT_WITNESS_SUPPORT",
        )

    def test_mismatch_does_not_validate(self):
        result = validate_against_witness(
            ["a","c","b"],
            ["a","b","c"],
        )
        self.assertFalse(result["exact_on_common_units"])

if __name__ == "__main__":
    unittest.main()
