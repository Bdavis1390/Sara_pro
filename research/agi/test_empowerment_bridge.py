import unittest
from empowerment_bridge import (
    AgencyCapability,
    mutual_information,
    safe_agency_index,
    agency_readiness,
)

class EmpowermentBridgeTests(unittest.TestCase):
    def test_perfect_binary_control_is_one_bit(self):
        joint = {
            ("left","L"):0.5,
            ("left","R"):0.0,
            ("right","L"):0.0,
            ("right","R"):0.5,
        }
        self.assertAlmostEqual(mutual_information(joint),1.0)

    def test_no_control_is_zero_bits(self):
        joint = {
            ("left","L"):0.25,
            ("left","R"):0.25,
            ("right","L"):0.25,
            ("right","R"):0.25,
        }
        self.assertAlmostEqual(mutual_information(joint),0.0)

    def test_safe_cannot_exceed_authorized(self):
        c = AgencyCapability("robot",4.0,3.0,2.0,2.5)
        with self.assertRaises(ValueError):
            c.validate()

    def test_safe_agency_requires_more_than_power(self):
        c = AgencyCapability("robot",4.0,3.0,2.0,2.0)
        good = safe_agency_index(c,1.0,1.0,1.0)
        poor_epistemics = safe_agency_index(c,0.2,1.0,1.0)
        self.assertGreater(good,poor_epistemics)

    def test_full_loop_is_testable_bounded_agency(self):
        self.assertEqual(
            agency_readiness(True,True,True,True,True,True),
            "BOUNDED_GENERAL_AGENCY_TESTABLE",
        )

if __name__ == "__main__":
    unittest.main()
