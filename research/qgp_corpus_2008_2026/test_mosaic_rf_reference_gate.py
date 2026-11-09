#!/usr/bin/env python3
"""Offline published MOSAIC-RF reference data and beam-equivalence regression."""
import math
import unittest
from mosaic_rf_reference_gate import (
    build, equivalence, DIRECTIONS, MODES, POWER_MARGIN_DB,
    greatcircle, S11_DB, S21_DB, S22_DB
)

class MosaicReferenceGateTests(unittest.TestCase):
    def test_published_geometry_has_nine_distinct_beam_targets(self):
        self.assertEqual(len(DIRECTIONS),9)
        self.assertEqual(len(MODES),9)
        self.assertEqual(len(equivalence(10)),36)
    def test_nominal_strict_equivalence_is_empty(self):
        report=build(10)
        gate=report["same_radiation_objective_test"]
        self.assertEqual(gate["number_of_equivalent_direction_pairs"],0)
        self.assertAlmostEqual(gate["minimum_3D_separation_deg"],28.480005,places=4)
        self.assertFalse(report["MOSAIC_R4_gate"]["supports_original_state_equivalence_H1"])
    def test_off_axis_angle_not_equal_to_azimuth_step(self):
        a=DIRECTIONS[1];b=DIRECTIONS[2]
        self.assertAlmostEqual(b["phi_deg"]-a["phi_deg"],45.)
        self.assertAlmostEqual(greatcircle(a,b),28.480005,places=4)
        self.assertAlmostEqual(greatcircle(DIRECTIONS[0],a),40.,places=7)
    def test_broader_tolerance_does_not_prove_equal_patterns(self):
        self.assertEqual(sum(p["equivalent_under_pointing_tolerance"] for p in equivalence(20)),0)
        self.assertGreater(sum(p["equivalent_under_pointing_tolerance"] for p in equivalence(30)),0)
        self.assertIn("pattern shape",build(10)["limits"][1])
    def test_published_power_margin_convention_reconciles(self):
        report=build(10)
        b=report["benchmark"]
        self.assertAlmostEqual(b["mean_power_margin_dB_arithmetic"],7.602222222,places=6)
        self.assertAlmostEqual(b["mean_power_margin_dB_linear_power_ratio"],8.343173912,places=6)
        self.assertAlmostEqual(b["published_rounded_mean_margin_dB"],8.34,places=2)
        self.assertEqual(len(POWER_MARGIN_DB),9)
    def test_port_data_are_not_intermodulation_data(self):
        report=build(10)
        self.assertEqual([len(S11_DB),len(S21_DB),len(S22_DB)],[9,9,9])
        self.assertTrue(report["MOSAIC_R4_gate"]["source_paper_port_data_are_not_IM3_measurements"])
        self.assertFalse(report["MOSAIC_R4_gate"]["novel_physics_demonstrated"])
        self.assertEqual(report["benchmark"]["physical_mode_to_direction_map"],"NOT_ASSERTED_FROM_DIRECTION_SET")
    def test_geometry_tolerance_validated(self):
        with self.assertRaises(ValueError): equivalence(0)
        with self.assertRaises(ValueError): equivalence(91)
if __name__=="__main__":unittest.main(verbosity=2)
