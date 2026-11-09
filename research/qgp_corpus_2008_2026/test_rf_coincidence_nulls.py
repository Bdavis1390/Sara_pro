#!/usr/bin/env python3
"""Regression tests: frequency coincidence null is post-selection diagnostic."""
import json,math,pathlib,tempfile,unittest
import numpy as np
from rf_coincidence_nulls import NOMINAL,COEFF,simulate
class CoincidenceTests(unittest.TestCase):
 def test_zero_spread_recovers_observed_frequency_separation(self):
  minima,spec=simulate(1200,0.,20261108,chunk=500)
  self.assertTrue(np.allclose(minima,.00256,atol=1e-10))
  self.assertTrue(np.allclose(spec,.00256,atol=1e-10))
 def test_varying_frequency_sets_change_nearest_separation(self):
  minima,spec=simulate(3000,.10,20261108)
  self.assertLess(float(np.min(minima)),.00256)
  self.assertGreater(float(np.max(minima)),.00256)
  self.assertTrue(np.all(minima>=0))
 def test_reproducible_random_seed(self):
  a,b=simulate(1357,.02,20261108,chunk=200)
  c,d=simulate(1357,.02,20261108,chunk=500)
  self.assertTrue(np.array_equal(a,c))
  self.assertTrue(np.array_equal(b,d))
 def test_no_confirmation_claim_in_preserved_output(self):
  p=pathlib.Path(__file__).resolve().parent/"rf_coincidence_nulls_results.json"
  j=json.loads(p.read_text())
  self.assertFalse(j["new_physics"])
  self.assertEqual(len(j["null_scenarios"]),3)
  self.assertTrue(all(x["number_of_simulated_frequency_sets"]==50000 for x in j["null_scenarios"]))
if __name__=="__main__":unittest.main(verbosity=2)
