#!/usr/bin/env python3
"""Offline-only RF detuning tests; all generated data are SYNTHETIC_TEST."""
import csv,pathlib,random,tempfile,unittest
from rf_intermod_prior import PAIRS,overlaps,products
from rf_detuning_gate import analyze
COLS=["pair_id","sample_type","detune_id","f_low_hz","f_high_hz",
      "observed_peak_hz","frequency_uncertainty_hz","instrument_id",
      "calibration_id","data_origin"]
def make_rows(pair,mode,include_blank=True,collinear=False,mixed_origin=False):
 lo,hi=PAIRS[pair]
 l=float(lo)*1e9;h=float(hi)*1e9
 rng=random.Random(20261109)
 rows=[]
 for a in (-3e6,0,3e6):
  for b in (-4e6,0,4e6):
   if collinear:b=a
   for sample in (["CANDIDATE","BLANK"] if include_blank else ["CANDIDATE"]):
    if mode=="mix":
     f=abs((-2*(l+a)+(h+b)) if pair=="WS-RF-001" else (-(l+a)+2*(h+b)))
    elif mode=="fixed":f=abs(-2*l+h)
    elif mode=="unmatched":f=1.5e9 + .41*a+.37*b
    else:raise ValueError("Unknown synthetic mode")
    f+=rng.uniform(-350,350)
    rows.append({"pair_id":pair,"sample_type":sample,
      "detune_id":f"D{int(a)}_{int(b)}",
      "f_low_hz":str(l+a),"f_high_hz":str(h+b),
      "observed_peak_hz":str(f),"frequency_uncertainty_hz":"20000",
      "instrument_id":"SYNTHETIC_NO_HARDWARE",
      "calibration_id":"CAL-SYNTHETIC_ONLY",
      "data_origin":"MEASURED_UNVERIFIED" if mixed_origin and sample=="BLANK" else "SYNTHETIC_TEST"})
 return rows
def apply(rows):
 with tempfile.TemporaryDirectory() as tmp:
  p=pathlib.Path(tmp)/"SYNTHETIC_DATA.csv"
  with p.open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=COLS);w.writeheader();w.writerows(rows)
  return analyze(p)
class DetuningTests(unittest.TestCase):
 def test_cross_pair_exact_arithmetic(self):
  overlaps10=overlaps()
  self.assertEqual(len(overlaps10),1)
  self.assertEqual(overlaps10[0]["separation_MHz"],"2.56000")
  self.assertEqual(overlaps10[0]["source_A"]["frequency_GHz"],"1.59256")
  self.assertEqual(overlaps10[0]["source_B"]["frequency_GHz"],"1.590")
 def test_pair1_expected_mixing(self):
  v=apply(make_rows("WS-RF-001","mix"))
  r=v["pairs"][0]
  self.assertEqual(r["candidate"]["classification"],"CONSISTENT_WITH_STANDARD_FREQUENCY_MIXING")
  self.assertEqual(r["blank"]["classification"],"CONSISTENT_WITH_STANDARD_FREQUENCY_MIXING")
  self.assertEqual((r["candidate"]["best_standard_model"]["m_low"],r["candidate"]["best_standard_model"]["n_high"]),(-2,1))
  self.assertTrue(v["synthetic"]);self.assertEqual(v["discovery_gate"],"BLOCKED")
 def test_pair3_expected_mixing(self):
  v=apply(make_rows("WS-RF-003","mix"))
  self.assertEqual((v["pairs"][0]["candidate"]["best_standard_model"]["m_low"],v["pairs"][0]["candidate"]["best_standard_model"]["n_high"]),(-1,2))
 def test_fixed_external_spur(self):
  v=apply(make_rows("WS-RF-001","fixed"))
  self.assertEqual(v["pairs"][0]["candidate"]["classification"],"CONSISTENT_WITH_FIXED_FREQUENCY_INTERFERENCE")
  self.assertEqual(v["discovery_gate"],"BLOCKED")
 def test_unmatched_cannot_claim_new_physics(self):
  v=apply(make_rows("WS-RF-001","unmatched"))
  self.assertEqual(v["pairs"][0]["candidate"]["classification"],"UNMATCHED_LIMITED_CATALOG_REVIEW_REQUIRED")
  self.assertEqual(v["discovery_gate"],"BLOCKED")
 def test_collinear_oscillator_detuning_rejected(self):
  with self.assertRaisesRegex(ValueError,"collinear"):
   apply(make_rows("WS-RF-001","mix",collinear=True))
 def test_missing_blank_rejected(self):
  with self.assertRaisesRegex(ValueError,"Candidate and blank"):
   apply(make_rows("WS-RF-001","mix",include_blank=False))
 def test_mixed_measured_synthetic_origin_rejected(self):
  with self.assertRaisesRegex(ValueError,"uniform data_origin"):
   apply(make_rows("WS-RF-001","mix",mixed_origin=True))
if __name__=="__main__":unittest.main(verbosity=2)
