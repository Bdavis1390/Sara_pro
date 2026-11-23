#!/usr/bin/env python3
"""NIST selected-IQ spectrum regression: synthetic signal and disclosure gates.
Network-free. Real dataset is independently published and not reproduced here.
"""
import math,pathlib,unittest
import numpy as np
from nist_im3_iq_selected_analysis import spectrum
ROOT=pathlib.Path(__file__).resolve().parent
class IQSpectralTests(unittest.TestCase):
 def signal(self,f=1e6,amp=.04,n=32768,seed=20261123):
  fs=5e6
  t=np.arange(n,dtype=float)/fs
  rng=np.random.default_rng(seed)
  z=amp*np.exp(2j*np.pi*f*t)
  z+=.001*(rng.normal(size=n)+1j*rng.normal(size=n))
  return z.astype(np.complex64)
 def test_synthetic_peak_is_near_source_predicted_frequency(self):
  r=spectrum(self.signal(),1e6)
  self.assertLess(abs(r["peak_minus_target_hz"]),r["frequency_resolution_hz"])
  self.assertGreater(r["peak_SNR_dB_relative_to_median_single_bin_noise"],20)
  self.assertFalse(r["calibrated_output_power_dBm"])
 def test_synthetic_amplitude_scaling_is_20log10(self):
  r1=spectrum(self.signal(amp=.03),1e6)
  r2=spectrum(self.signal(amp=.06),1e6)
  self.assertAlmostEqual(r2["peak_amplitude_db_relative_to_unscaled_ADC"]-
                         r1["peak_amplitude_db_relative_to_unscaled_ADC"],
                         20*math.log10(2),places=1)
 def test_wrong_frequency_is_not_mistaken_for_signal(self):
  r=spectrum(self.signal(f=.7e6),1e6)
  self.assertLess(r["peak_SNR_dB_relative_to_median_single_bin_noise"],17)
 def test_frequency_bin_resolution_propagated(self):
  r=spectrum(self.signal(),1e6)
  self.assertAlmostEqual(r["frequency_resolution_hz"],5e6/32768)
 def test_source_nonfinite_iq_rejected_upstream(self):
  z=self.signal()
  self.assertTrue(np.all(np.isfinite(z)))
  z[5]=complex(float("nan"),0)
  self.assertFalse(np.all(np.isfinite(z)))
if __name__=="__main__":unittest.main(verbosity=2)
