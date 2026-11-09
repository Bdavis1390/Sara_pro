#!/usr/bin/env python3
"""Synthetic regression tests for no-coupling RF beating baseline."""
import json,math,pathlib,tempfile,unittest
import numpy as np
from rf_four_tone_beating_baseline import DELTA,OUT_A,OUT_C,normalized_envelope,PHI_A,PHI_C
class FourToneBeatTests(unittest.TestCase):
 def test_frequency_separation_and_period(self):
  self.assertAlmostEqual(DELTA/1e6,2.56,places=8)
  self.assertAlmostEqual(1e9/DELTA,390.625,places=8)
 def test_constructive_and_destructive_interference(self):
  self.assertAlmostEqual(float(normalized_envelope([0])[0]),4,places=12)
  self.assertAlmostEqual(float(normalized_envelope([.5/DELTA])[0]),0,places=12)
  self.assertAlmostEqual(float(normalized_envelope([1/DELTA])[0]),4,places=12)
 def test_phase_cycling_tunes_beat_without_coupling(self):
  self.assertAlmostEqual(float(normalized_envelope([0],phase_a=math.pi/2)[0]),2,places=12)
  self.assertAlmostEqual(float(normalized_envelope([0],phase_a=math.pi)[0]),0,places=12)
  self.assertAlmostEqual(PHI_A(math.pi/2,math.pi),0,places=12)
  self.assertAlmostEqual(PHI_C(math.pi/2,math.pi),3*math.pi/2,places=12)
 def test_beat_mean_is_incoherent_sum(self):
  t=np.linspace(0,100/DELTA,50000,endpoint=False)
  v=normalized_envelope(t,amp_a=.6,amp_c=.8)
  self.assertAlmostEqual(np.mean(v),1.0,places=10)
  self.assertAlmostEqual(np.max(v),1.96,places=10)
  self.assertAlmostEqual(np.min(v),.04,places=10)
 def test_result_not_physical_observation(self):
  p=pathlib.Path(__file__).resolve().parent/"rf_four_tone_beating_baseline.json"
  j=json.loads(p.read_text())
  self.assertFalse(j["new_physics"])
  self.assertIn("NO_MEASUREMENTS",j["scope"])
  self.assertAlmostEqual(j["baseband_beat_period_ns"],390.625,places=8)
if __name__=="__main__":unittest.main(verbosity=2)
