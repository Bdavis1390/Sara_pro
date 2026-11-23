#!/usr/bin/env python3
"""Post-selection NIST IM3 quality-control checks without network activity."""
import json,pathlib,tempfile,unittest
import numpy as np
from nist_im3_quality_gate import summarize
ROOT=pathlib.Path(__file__).resolve().parent
MEASURED=ROOT/"external_measured/nist_2628/receiver_pair_crosscheck.json"

def synthetic_report():
 def v(idx,p,amp,snr,frequency):
  return {"index":idx,"source_input_power_each_dBm":p,
    "measurement":{"peak_IF_hz":frequency,
      "peak_amplitude_db_relative_to_unscaled_ADC":amp,
      "peak_SNR_dB_relative_to_median_single_bin_noise":snr}}
 return {"measurement_type":"THIRD_PARTY_NIST_MEASURED_IQ_RECEIVER_NONLINEARITY",
 "remote_archive":"SYNTHETIC_ONLY.zip",
 "terminated_receiver_reference":{"peak_SNR_dB_relative_to_median_single_bin_noise":11.6},
 "selected_samples":[v(0,-20,-114,10,992000),v(1,-12,-104,22,1001500),
                     v(2,-9,-95,32,1001490),v(3,-7,-89,39,1001480)]}
def analyze_synthetic(obj):
 with tempfile.TemporaryDirectory() as d:
  path=pathlib.Path(d)/"SYNTHETIC_ONLY.json"
  path.write_text(json.dumps(obj))
  return summarize(path)

class QualityFilterUnitTests(unittest.TestCase):
 def test_winner_of_many_noise_bins_is_not_discovery(self):
  r=analyze_synthetic(synthetic_report())
  self.assertEqual(r["qualified_captures"],3)
  self.assertEqual(r["excluded_captures"],1)
  self.assertFalse(r["new_physics_demonstrated"])
  self.assertFalse(r["per_capture"][0]["accepted_for_exploratory_slope"])
 def test_reject_mismatched_capture_frequency(self):
  data=synthetic_report()
  data["selected_samples"][1]["measurement"]["peak_IF_hz"]=1005000
  with self.assertRaisesRegex(ValueError,"Less than 3 strong"):
   analyze_synthetic(data)
 def test_reject_misclassified_source(self):
  x=synthetic_report()
  x["measurement_type"]="ORIGINAL_WORLDSHEPHERD_HARDWARE"
  with self.assertRaisesRegex(ValueError,"misclassified"):
   analyze_synthetic(x)
 def test_weak_inputs_provide_no_slope(self):
  x=synthetic_report()
  for sample in x["selected_samples"]:
   sample["measurement"]["peak_SNR_dB_relative_to_median_single_bin_noise"]=12
  r=analyze_synthetic(x)
  self.assertEqual(r["state"],"INSUFFICIENT_RELIABLE_SIGNAL")
@unittest.skipUnless(MEASURED.exists(),"Measured NIST summary unavailable; rerun bounded selective capture")
class NISTRealDataAcceptanceTests(unittest.TestCase):
 def test_two_receivers_have_explicit_ordinary_physics_status(self):
  report=json.loads(MEASURED.read_text())
  self.assertFalse(report["new_physics"])
  self.assertEqual(len(report["sources"]),2)
  s0,s1=report["sources"]
  self.assertEqual([s0["qualified_captures"],s1["qualified_captures"]],[3,4])
  self.assertEqual([s0["excluded_captures"],s1["excluded_captures"]],[2,0])
  self.assertAlmostEqual(s0["fit_linear_slope_dB_output_per_dB_input"],3.344454379,places=6)
  self.assertAlmostEqual(s1["fit_linear_slope_dB_output_per_dB_input"],2.996276406,places=6)
  self.assertTrue(all(not v["new_physics_demonstrated"] for v in report["sources"]))
if __name__=="__main__":unittest.main(verbosity=2)
