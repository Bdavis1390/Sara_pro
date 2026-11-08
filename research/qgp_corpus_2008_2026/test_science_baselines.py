#!/usr/bin/env python3
"""Offline regression tests for WorldShepherd STAR-derived benchmark reductions."""
import hashlib,json,pathlib,unittest,math
ROOT=pathlib.Path(__file__).resolve().parent
def load(rel):return json.loads((ROOT/rel).read_text())
class PublishedSTARBenchmarkTests(unittest.TestCase):
 def test_26_hepdata_tables_recover_exact_sources(self):
  p=ROOT/"external_models/star_baryon_2026/hepdata_154708"
  j=load("external_models/star_baryon_2026/hepdata_154708/manifest.json")
  self.assertEqual(len(j["tables"]),26)
  for x in j["tables"]:
   raw=(p/("table_%02d.json"%x["id"])).read_bytes()
   self.assertEqual(hashlib.sha256(raw).hexdigest(),x["sha256"])
   self.assertEqual(json.loads(raw)["table_license"]["name"],"CC0")
 def test_2026_slope_matches_published(self):
  j=load("external_models/star_baryon_2026/rapidity_slope_consistency.json")
  a=j["systematic_cross_bin_correlation_scan"]["0"];b=j["published_comparator"]
  self.assertLess(abs(a["slope"]-b["slope"]),2*math.hypot(a["slope_sigma_assumed"],b["sigma"]))
  self.assertLess(abs(a["slope_sigma_assumed"]-j["bootstrap_rho0"]["sd"]),0.02)
 def test_2026_model_tension_not_claimed_as_discovery(self):
  j=load("external_models/star_baryon_2026/model_comparison_2026.json")
  self.assertEqual(len(j["measured_ratio"]),5)
  self.assertTrue(all(v>m for v,m in zip(j["measured_ratio"],j["comparison"]["UrQMD"]["predictions"])))
  self.assertEqual(j["evidence_state"],"PUBLISHED_MODEL_COMPARISON_REPRODUCED_NO_NEW_PHYSICS")
 def test_2025_thermal_spectrum_matches_reported_scale(self):
  j=load("external_models/star_baryon_2026/star_2025_imr_fit.json")
  for k in ("27_GeV","54.4_GeV"):
   fit=j["result"][k]["primary"]
   self.assertLess(abs(fit["T_MeV"]-j["baseline_published_IMR_T_MeV"][k]),140)
   self.assertTrue(fit["dof"]>=4)
  self.assertFalse(j["novel_physics"])
if __name__=="__main__":unittest.main(verbosity=2)
