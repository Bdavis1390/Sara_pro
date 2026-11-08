#!/usr/bin/env python3
"""Deterministic SYNTHETIC tests for RF measurement gate; zero real RF transmissions."""
import csv,pathlib,tempfile,unittest,random
from rf_measurement_gate import analyze

PAIRS={"WS-RF-001":5562490000,"WS-RF-002":711000000,
       "WS-RF-003":597000000,"SHAM":300000000}
FIELDNAMES=["experiment_id","pair_id","replicate_id","sample_type","condition",
    "output_frequency_hz","output_power_dbm","uncertainty_db",
    "instrument_id","calibration_id","timestamp_utc","data_origin"]

def generate(path,inject=False,bad_calibration=False,omit_sham=False,omit_ab=False):
 rng=random.Random(20261108)
 rows=[]
 for pair,hz in PAIRS.items():
  if omit_sham and pair=="SHAM":continue
  for rep in range(8):
   jitter=rng.uniform(-.08,.08)
   for typ in ("CANDIDATE","BLANK"):
    for condition in ("OFF","A","B","AB"):
     if omit_ab and typ=="CANDIDATE" and rep==2 and condition=="AB" and pair=="WS-RF-001":continue
     if inject and pair!="SHAM" and typ=="CANDIDATE" and condition=="AB":
      dbm=-64.0+jitter
     else:
      dbm=-90.0+jitter
     rows.append({
       "experiment_id":"SYNTH-NEVER-CLAIM-MEASURED",
       "pair_id":pair,"replicate_id":"SYNTH-R%d"%rep,
       "sample_type":typ,"condition":condition,
       "output_frequency_hz":str(hz),"output_power_dbm":str(dbm),
       "uncertainty_db":"0.12","instrument_id":"SYNTH-ANALYZER",
       "calibration_id":"WRONG" if bad_calibration else "CAL-SYNTHETIC-NOT-REAL",
       "timestamp_utc":"2026-11-08T12:00:00Z",
       "data_origin":"SYNTHETIC_TEST"})
 with open(path,"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=FIELDNAMES);w.writeheader();w.writerows(rows)
class Tests(unittest.TestCase):
 def run_dataset(self,**options):
  with tempfile.TemporaryDirectory() as root:
   path=pathlib.Path(root)/"SYNTHETIC_INPUT.csv"
   generate(path,**options)
   return analyze(path)
 def test_null_is_not_discovery(self):
  r=self.run_dataset()
  self.assertTrue(r["synthetic_test"])
  self.assertEqual(r["fundamental_discovery_gate"],"BLOCKED")
  self.assertTrue(all(abs(x["paired_interaction_difference_W"])<1e-21 for x in r["results"]))
  self.assertTrue(all(x["exact_sign_flip_two_sided_p"]==1.0 for x in r["results"]))
 def test_positive_standard_nonlinearity_not_new_physics(self):
  r=self.run_dataset(inject=True)
  self.assertTrue(r["synthetic_test"])
  sig=[x for x in r["results"] if x["pair_id"]!="SHAM"]
  self.assertEqual(len(sig),3)
  self.assertTrue(all(x["holm_adjusted_p_across_tested_outputs"]<=0.05 for x in sig))
  self.assertTrue(all(x["claim_status"]=="NO_NEW_PHYSICS_INFERABLE_FROM_INTERACTION_ALONE" for x in sig))
  self.assertEqual(r["fundamental_discovery_gate"],"BLOCKED")
 def test_missing_sham_rejected(self):
  with self.assertRaisesRegex(ValueError,"sham"):
   self.run_dataset(omit_sham=True)
 def test_missing_condition_rejected(self):
  with self.assertRaisesRegex(ValueError,"Incomplete"):
   self.run_dataset(omit_ab=True)
 def test_bad_calibration_id_rejected(self):
  with self.assertRaisesRegex(ValueError,"calibration"):
   self.run_dataset(bad_calibration=True)
if __name__=="__main__":unittest.main(verbosity=2)
