#!/usr/bin/env python3
"""Conventional two-port topology reference and third-party measured-data gates."""
import pathlib, unittest
import numpy as np
from rf_series_shunt_baseline import compare,analyze
ROOT=pathlib.Path(__file__).resolve().parent
EXTERNAL=ROOT/"external_measured/terrameta_20186567/raw"

def constant_twoport(s11,s21,n=800):
 S=np.zeros((n,2,2),dtype=complex)
 S[:,0,0]=S[:,1,1]=s11
 S[:,1,0]=S[:,0,1]=s21
 return S

class TheoreticalTopologyTests(unittest.TestCase):
 def setUp(self):
  self.f=np.linspace(70000,10e9,800)
  self.thru=constant_twoport(0,1)
 def test_ideal_series_resistor_identity(self):
  # R=100 Ohm between two 50 Ohm ports: S11=.5, S21=.5
  S=constant_twoport(.5,.5)
  vals=compare(S,self.thru,self.f)
  self.assertAlmostEqual(vals[0]["median_series_identity_difference_from_thru"],0)
  self.assertAlmostEqual(vals[0]["median_shunt_identity_difference_from_thru"],1)
 def test_ideal_shunt_admittance_identity(self):
  # Shunt admittance Y*Z0=1: S21=2/3; S11=-1/3
  S=constant_twoport(-1/3,2/3)
  vals=compare(S,self.thru,self.f)
  self.assertAlmostEqual(vals[0]["median_shunt_identity_difference_from_thru"],0)
  self.assertAlmostEqual(vals[0]["median_series_identity_difference_from_thru"],2/3)
 def test_wrong_grid_rejected(self):
  with self.assertRaisesRegex(ValueError,"Different measured grids"):
   compare(constant_twoport(.5,.5),self.thru[:100],self.f)

@unittest.skipUnless(EXTERNAL.exists() and len(list(EXTERNAL.glob("*.S2P")))==12,"Third-party raw dataset not yet downloaded")
class PublisherMeasuredTests(unittest.TestCase):
 def test_two_thru_reference_sensitivity_and_non_discovery(self):
  r=analyze(EXTERNAL)
  self.assertEqual(len(r["device_state_results"]),9)
  self.assertTrue(r["all_measured_device_states_better_series_first_10GHz"])
  self.assertTrue(all(x["first_10_GHz_series_residual_median_over_refs"]<.007 for x in r["device_state_results"]))
  self.assertFalse(r["new_physics"])
  self.assertIn("not replace",r["limitations"][1])
if __name__=="__main__":unittest.main(verbosity=2)
