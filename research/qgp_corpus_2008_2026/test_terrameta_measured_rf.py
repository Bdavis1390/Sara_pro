#!/usr/bin/env python3
"""TERRAMETA real-data integrity and scientific-claim regression tests.
No raw third-party S2P files in public source tree. Tests using actual
published measurements skip when local data have not been acquired.
"""
import json,pathlib,tempfile,unittest
import numpy as np
from analyze_terrameta_measured_rf import read_s2p,interp_complex,analyze,classify
ROOT=pathlib.Path(__file__).resolve().parent
DATAROOT=ROOT/"external_measured/terrameta_20186567/raw"

class TouchstoneParserTests(unittest.TestCase):
 def test_frequency_ri_complex_touchstone_semantics(self):
  with tempfile.TemporaryDirectory() as td:
   path=pathlib.Path(td)/"tiny.S2P"
   freq=np.linspace(70000,160e9,800)
   with path.open("w") as out:
    out.write("# Hz S RI R 50\n")
    for f in freq:out.write(f"{f:.3f} 0 0 0.7 0.1 0.7 0.1 0 0\n")
   f,S=read_s2p(path)
   self.assertEqual(len(f),800)
   self.assertAlmostEqual(S[123,1,0].real,.7)
   self.assertAlmostEqual(S[123,0,1].imag,.1)
   predicted,bracket=interp_complex(f,S,3.96993e9)
   self.assertAlmostEqual(predicted[1,0].real,.7)
   self.assertGreater(bracket[1]-bracket[0],200e6)
 def test_reject_wrong_format(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/"wrong.S2P"
   p.write_text("# GHz S DB R 50\n"+"70000 0 0 0.7 0.1 0.7 0.1 0 0\n"*800)
   with self.assertRaisesRegex(ValueError,"Unsupported Touchstone"):
    read_s2p(p)
 def test_reject_file_name_spoofing(self):
  with self.assertRaisesRegex(ValueError,"Unrecognized"):
   classify("fake_measured_breakthrough.S2P")

@unittest.skipUnless(DATAROOT.exists() and len(list(DATAROOT.glob("*.S2P")))==12,"External measured files not present locally; fetch from publisher first")
class ExternalPublishedMeasurementsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=analyze(DATAROOT)
 def test_all_twelve_revalidated_by_sha256(self):
  j=self.report
  self.assertEqual(j["actual_measurements_derived_from"],12)
  self.assertEqual(j["freq_sample_count"],800)
  self.assertTrue(j["raw_sha256_reverified"])
  self.assertFalse(j["original_novel_physics_demonstrated"])
  self.assertEqual(j["worldshepherd_original_measurements"],0)
 def test_spacing_far_exceeds_cross_pair_2p56_MHz(self):
  j=self.report
  self.assertGreater(j["grid_spacing_over_near_coincidence_separation"],75)
  self.assertLess(j["grid_spacing_over_near_coincidence_separation"],80)
  for row in j["files"]:
   for p in row["targets"]:
    self.assertFalse(p["is_directly_measured_at_target"])
    self.assertEqual(p["interpolation_uncertainty"],"NOT_ESTABLISHED")
 def test_state_dependent_contrast_is_external_known_physics(self):
  a=[x for x in self.report["device_state_comparisons"] if x["device_id"]==2]
  f3=next(x for x in a if x["frequency_GHz"]==3.96993)
  f9=next(x for x in a if x["frequency_GHz"]==9.53242)
  self.assertGreater(f3["LRS_minus_HRS_median_S21_dB"],8.0)
  self.assertGreater(f9["LRS_minus_HRS_median_S21_dB"],3.0)
  self.assertFalse(self.report["original_novel_physics_demonstrated"])
 def test_shared_upper_band_nonpassivity_is_not_new_energy(self):
  import numpy as np
  through=next(p for p in self.report["files"] if p["file"]=="02_THRU_1.S2P")
  self.assertGreater(through["passivity_flag_gt_1p02_count"],200)
  freq,S=read_s2p(DATAROOT/"02_THRU_1.S2P")
  sing=np.linalg.svd(S,compute_uv=False)[:,0]
  self.assertFalse(np.any(sing[freq<80e9]>1.02))
  self.assertTrue(np.all(sing[freq>=120e9]>1.02))
 def test_source_metadata_license_not_inferred(self):
  j=json.loads((DATAROOT.parent/"terrameta_local_manifest.json").read_text())
  self.assertFalse(j["rights_metadata_present"])
  self.assertIn("NO_REPUBLICATION",j["license_reuse_status"])

if __name__=="__main__":unittest.main(verbosity=2)
