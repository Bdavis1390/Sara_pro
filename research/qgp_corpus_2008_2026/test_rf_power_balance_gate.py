#!/usr/bin/env python3
"""Synthetic-only validation for RF passivity/power budget gate."""
import csv,pathlib,tempfile,unittest
from rf_power_balance_gate import BASE,CHANNELS,analyze
FIELDS=sorted(BASE|{f"p_{c}_w" for c in CHANNELS}|{f"u_{c}_w" for c in CHANNELS})
def make_rows(excess=False,missing=False,active=False,bad_origin=False):
 rows=[]
 for rep in range(3):
  for sample in ("CANDIDATE","BLANK"):
   for cond,p in (("OFF",0.),("A",.005),("B",.004),("AB",.009)):
    if missing and rep==1 and sample=="BLANK" and cond=="B":continue
    vals={"input":p,"reflected":p*.1,"transmitted":p*.4,
          "radiated":p*.05,"heat":p*.45,"stored":0.,"other":0.}
    if excess and sample=="CANDIDATE" and cond=="AB":
     vals["transmitted"]+=.002
    r={"experiment_id":"SYNTHETIC_NO_PHYSICAL_DATA","replicate_id":f"R{rep}",
       "pair_id":"WS-RF-001","sample_type":sample,"condition":cond,
       "instrument_id":"SYNTHETIC_METER","calibration_id":"CAL-SYNTHETIC_NOT_VALID",
       "timestamp_utc":"2026-11-09T01:00:00Z",
       "data_origin":"MEASURED_UNVERIFIED" if bad_origin else "SYNTHETIC_TEST",
       "device_class":"ACTIVE" if active else "PASSIVE",
       "coverage_status":"ALL_PORTS_ACCOUNTED_MEASURED_OR_BOUNDED"}
    for k,v in vals.items():
     r[f"p_{k}_w"]=str(v)
     r[f"u_{k}_w"]=str(.00005 if p else .00001)
    rows.append(r)
 return rows
def evaluate(**kwargs):
 with tempfile.TemporaryDirectory() as td:
  p=pathlib.Path(td)/"TEST_SYNTHETIC.csv"
  rows=make_rows(**kwargs)
  with p.open("w",newline="") as f:
   writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
  return analyze(p)
class PowerBudgetTests(unittest.TestCase):
 def test_closed_budget_is_only_preliminary(self):
  x=evaluate()
  self.assertEqual(x["number_of_rows"],24)
  self.assertEqual(x["nonclosure_count"],0)
  self.assertFalse(x["novel_physics_demonstrated"])
  self.assertEqual(x["discovery_gate"],"BLOCKED")
  self.assertEqual(x["data_origin"],"SYNTHETIC_TEST")
 def test_apparent_excess_power_does_not_prove_novel_physics(self):
  x=evaluate(excess=True)
  self.assertEqual(x["nonclosure_count"],3)
  self.assertTrue(all(r["diagnostic_z_diagonal_only"] < -3 for r in x["conditions"]
                      if r["sample_type"]=="CANDIDATE" and r["condition"]=="AB"))
  self.assertFalse(x["novel_physics_demonstrated"])
 def test_missing_condition_rejected(self):
  with self.assertRaisesRegex(ValueError,"Missing OFF/A/B/AB"):
   evaluate(missing=True)
 def test_active_device_rejected(self):
  with self.assertRaisesRegex(ValueError,"Active/pumped"):
   evaluate(active=True)
 def test_synthetic_calibration_cannot_be_measured(self):
  with self.assertRaisesRegex(ValueError,"Synthetic calibration"):
   evaluate(bad_origin=True)
if __name__=="__main__":unittest.main(verbosity=2)
