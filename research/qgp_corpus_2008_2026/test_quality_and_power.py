#!/usr/bin/env python3
"""Offline checks: HEPData quality gates and RF synthetic design sensitivity."""
import json,pathlib,unittest
import audit_hepdata_quality
import rf_design_power
ROOT=pathlib.Path(__file__).resolve().parent
class AuditAndPowerTests(unittest.TestCase):
 def table(self,n):
  p=ROOT/"external_models/star_baryon_2026/hepdata_154708"/("table_%02d.json"%n)
  return json.loads(p.read_text())
 def test_quarantine_placeholder_charge_table(self):
  a=audit_hepdata_quality.audit(self.table(25))
  self.assertEqual(a["automated_status"],"QUARANTINE_FOR_MANUAL_VERIFICATION")
  self.assertTrue(a["dependent_groups"]["0"]["all_zero"])
 def test_partial_placeholder_groups_neutron_not_all_zero(self):
  a=audit_hepdata_quality.audit(self.table(24))
  self.assertEqual(a["automated_status"],"QUARANTINE_FOR_MANUAL_VERIFICATION")
  self.assertTrue(a["dependent_groups"]["0"]["all_values_identical"])
  self.assertFalse(a["dependent_groups"]["2"]["all_values_identical"])
 def test_primary_baryon_ratio_not_quarantined(self):
  a=audit_hepdata_quality.audit(self.table(3))
  self.assertEqual(a["automated_status"],"STRUCTURALLY_PLAUSIBLE_UNVALIDATED")
  self.assertEqual(a["rows"],5)
 def test_exact_minimum_with_four_outputs(self):
  self.assertGreater(2*4/(2**7),.05)
  self.assertLess(2*4/(2**8),.05)
  self.assertEqual(rf_design_power.sign_matrix(8).shape,(256,8))
 def test_synthetic_absent_effect_suppression(self):
  import numpy as np
  r=rf_design_power.estimate(8,0.0,150,np.random.default_rng(20261108),m=4)
  self.assertLess(r["candidate_detection_rate"],.15)
  self.assertLess(r["at_least_one_false_positive_rate"],.15)
if __name__=="__main__":unittest.main(verbosity=2)
