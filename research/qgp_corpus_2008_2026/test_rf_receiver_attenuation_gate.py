#!/usr/bin/env python3
"""Synthetic-only tests for receiver-side attenuation artifact gate."""
import csv,pathlib,tempfile,unittest
from rf_receiver_attenuation_gate import NEEDED,analyze
def rows(cand_slope=-1.,blank_slope=-3.,invalid_tone=False,missing_pad=False,
         bad_origin=False,noise_margin=18.,changed_sources=False):
 result=[]
 for k in range(3):
  for s in ("CANDIDATE","BLANK"):
   for a in (0.,6.,12.):
    if missing_pad and s=="BLANK" and k==0 and a==12.:continue
    slope=cand_slope if s=="CANDIDATE" else blank_slope
    x={
     "experiment_id":"SYNTHETIC_ONLY","pair_id":"WS-RF-001","sample_type":s,
     "replicate_id":f"TEST-R{k}","pad_loss_db":str(a),
     "tone_low_rx_dbm":str(-20.-a+(5 if invalid_tone and s=="BLANK" and a==12 else 0)),
     "tone_high_rx_dbm":str(-21.-a),
     "spur_raw_rx_dbm":str(-70+slope*a+.02*k),
     "spur_uncertainty_db":".15",
     "spur_above_noise_margin_db":str(noise_margin),
     "pad_calibration_id":"CAL-SYNTHETIC_PAD",
     "receiver_calibration_id":"CAL-SYNTHETIC_RX",
     "source_setting_id":"DIFFERENT" if changed_sources and s=="BLANK" else "FIXED_2_TONE",
     "timestamp_utc":"2026-11-09T00:00:00Z",
     "data_origin":"MEASURED_UNVERIFIED" if bad_origin else "SYNTHETIC_TEST"
    }
    result.append(x)
 return result
def run_case(**opts):
 with tempfile.TemporaryDirectory() as td:
  path=pathlib.Path(td)/"SYNTHETIC.csv"
  with path.open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=sorted(NEEDED));w.writeheader();w.writerows(rows(**opts))
  return analyze(path)
class AttenuationTests(unittest.TestCase):
 def test_pre_receiver_different_from_receiver_cubic(self):
  x=run_case()
  a=[r["classification"] for r in x["results"] if r["sample"]=="CANDIDATE"]
  b=[r["classification"] for r in x["results"] if r["sample"]=="BLANK"]
  self.assertEqual(set(a),{"PRE_RECEIVER_SPUR_SCALING_COMPATIBLE"})
  self.assertEqual(set(b),{"CUBIC_RECEIVER_IM3_SCALING_COMPATIBLE"})
  self.assertFalse(x["novel_physics_demonstrated"])
 def test_receiver_only_cubic_is_not_discovery(self):
  x=run_case(cand_slope=-3)
  self.assertTrue(all(r["classification"]=="CUBIC_RECEIVER_IM3_SCALING_COMPATIBLE" for r in x["results"]))
  self.assertEqual(x["discovery_gate"],"BLOCKED")
 def test_ambiguous_mixture_does_not_prove_new_physics(self):
  x=run_case(cand_slope=-2)
  self.assertTrue(any(r["classification"]=="OTHER_OR_INTERFERING_BEHAVIOR_REVIEW_REQUIRED" for r in x["results"]))
  self.assertEqual(x["discovery_gate"],"BLOCKED")
 def test_missing_pad_rejected(self):
  with self.assertRaisesRegex(ValueError,"3\\+ nonduplicate pads"):
   run_case(missing_pad=True)
 def test_tone_power_check_rejects_wrong_attenuator_location(self):
  with self.assertRaisesRegex(ValueError,"Incident tone-power"):
   run_case(invalid_tone=True)
 def test_changed_source_between_sample_and_blank_rejected(self):
  with self.assertRaisesRegex(ValueError,"Source settings differ"):
   run_case(changed_sources=True)
 def test_low_snr_rejected(self):
  with self.assertRaisesRegex(ValueError,"Censored/low-SNR"):
   run_case(noise_margin=2)
 def test_synthetic_calibration_cannot_claim_measurement(self):
  with self.assertRaisesRegex(ValueError,"Synthetic calibration"):
   run_case(bad_origin=True)
if __name__=="__main__":unittest.main(verbosity=2)
