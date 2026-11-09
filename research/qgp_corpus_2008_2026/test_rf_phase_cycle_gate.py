#!/usr/bin/env python3
"""Synthetic phase-cycle controls for conventional source-locked mixing.
All generated voltages are simulated and never physical measurement evidence.
"""
import csv,math,pathlib,random,tempfile,unittest
from rf_phase_cycle_gate import REQUIRED,analyze
def generate(pair="WS-RF-001",mode="material",missing_ref=False,
             changed_source=False,mixed_origin=False,duplicate=False):
 rng=random.Random(20261109)
 co={"WS-RF-001":(-2,1),"WS-RF-002":(-1,2),"WS-RF-003":(-1,2)}
 m,n=co[pair]
 rows=[]
 for k in range(3):
  for typ in ("CANDIDATE","BLANK","KNOWN_NONLINEAR_REFERENCE"):
   if missing_ref and typ=="KNOWN_NONLINEAR_REFERENCE":continue
   for il in range(4):
    for ih in range(4):
     pl=il*math.pi/2;ph=ih*math.pi/2
     angle=m*pl+n*ph
     common=.18+.10j
     if mode=="material":
      val=common+(.34-.16j if typ=="CANDIDATE" else 0j)
     elif mode=="all_receiver":val=common
     elif mode=="unmodeled":val=common
     else:raise ValueError("unknown test mode")
     if typ=="KNOWN_NONLINEAR_REFERENCE":val=common+(.32+.23j)
     z=val*complex(math.cos(angle),math.sin(angle)) + (.06-.03j)
     if mode=="unmodeled" and typ=="CANDIDATE":
      z+=.4*complex(math.cos(pl),math.sin(pl))
     z+=complex(rng.uniform(-.001,.001),rng.uniform(-.001,.001))
     rows.append({
       "experiment_id":"SYNTHETIC_EXPERIMENT_NOT_MEASURED",
       "pair_id":pair,"replicate_id":f"SYNTHETIC_R{k}",
       "sample_type":typ,"phase_low_rad":f"{pl:.12f}",
       "phase_high_rad":f"{ph:.12f}",
       "iq_real_v":f"{z.real:.12f}","iq_imag_v":f"{z.imag:.12f}",
       "iq_sigma_v":".01",
       "calibration_id":"CAL-SYNTHETIC_NOT_CERTIFIED",
       "reference_plane_id":"SYNTHETIC_REFERENCE_PLANE",
       "receiver_id":"SYNTHETIC_IQ_RECEIVER",
       "source_state_id":"CHANGED" if changed_source and typ=="BLANK" else "FIXED_SYNTHETIC",
       "data_origin":"MEASURED_UNVERIFIED" if mixed_origin and typ=="BLANK" else "SYNTHETIC_TEST"
     })
 if duplicate:rows.append(rows[0].copy())
 return rows
def run_case(**kw):
 with tempfile.TemporaryDirectory() as d:
  path=pathlib.Path(d)/"SYNTHETIC_PHASES.csv"
  with path.open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=sorted(REQUIRED));w.writeheader();w.writerows(generate(**kw))
  return analyze(path)
class PhaseCycleTests(unittest.TestCase):
 def test_nonlinear_sample_follows_standard_source_phase(self):
  j=run_case()
  self.assertTrue(j["synthetic_test"])
  self.assertEqual(j["matched_sessions"],3)
  self.assertEqual(j["rows"],144)
  self.assertTrue(all(x["fit_type"]=="CONVENTIONAL_PHASE_SIGNATURE_FIT_ACCEPTABLE" for x in j["results"]))
  self.assertTrue(all(.35<x["sample_source_locked_minus_blank_abs_v"]<.40 for x in j["results"]))
  self.assertEqual(j["discovery_gate"],"BLOCKED")
 def test_receiver_source_spur_alone_is_not_material(self):
  j=run_case(mode="all_receiver")
  self.assertTrue(all(x["blank_source_locked_fraction_of_candidate"]>.99 for x in j["results"]))
  self.assertTrue(all(x["sample_source_locked_minus_blank_abs_v"]<.005 for x in j["results"]))
  self.assertFalse(j["novel_physics_demonstrated"])
 def test_phase_mismatch_is_review_not_new_force(self):
  j=run_case(mode="unmodeled")
  self.assertTrue(all(x["fit_type"]=="UNMODELED_PHASE_RESPONSE_REQUIRES_ARTIFACT_REVIEW" for x in j["results"]))
  self.assertEqual(j["discovery_gate"],"BLOCKED")
 def test_other_pair_phase_signature(self):
  j=run_case(pair="WS-RF-003")
  self.assertTrue(all(x["fit_type"]=="CONVENTIONAL_PHASE_SIGNATURE_FIT_ACCEPTABLE" for x in j["results"]))
 def test_missing_nonlinear_reference_rejected(self):
  with self.assertRaisesRegex(ValueError,"known nonlinear reference"):
   run_case(missing_ref=True)
 def test_unmatched_source_settings_rejected(self):
  with self.assertRaisesRegex(ValueError,"Mismatched instrument"):
   run_case(changed_source=True)
 def test_false_measurement_origin_rejected(self):
  with self.assertRaisesRegex(ValueError,"Mixed/unknown data origin"):
   run_case(mixed_origin=True)
 def test_duplicate_phase_cycle_rejected(self):
  with self.assertRaisesRegex(ValueError,"Duplicate phase cycle point"):
   run_case(duplicate=True)
if __name__=="__main__":unittest.main(verbosity=2)
