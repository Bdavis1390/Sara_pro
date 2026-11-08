#!/usr/bin/env python3
"""Offline regression tests for safe QGP harvesting; absolutely no live API calls."""
import json, pathlib, subprocess, sys, tempfile, unittest
import urllib.error
from unittest import mock
import harvest_qgp
import screen_relevance

class IngestSafetyTests(unittest.TestCase):
 def test_rate_limit_is_not_retried(self):
  err=urllib.error.HTTPError("https://api.openalex.org/works",429,"Too Many Requests",{},None)
  with mock.patch("harvest_qgp.urllib.request.urlopen",side_effect=err) as stub:
   with self.assertRaises(urllib.error.HTTPError):
    harvest_qgp.get("https://api.openalex.org/works")
   self.assertEqual(stub.call_count,1)
 def test_classification_negative_control(self):
  self.assertEqual(screen_relevance.evaluate("Optimized Radiation Therapy for Oncology")[0],"UNCLASSIFIED_MANUAL_REVIEW")
 def test_classification_qgp(self):
  self.assertEqual(screen_relevance.evaluate("Quark-Gluon Plasma Transport Effects")[0],"CORE_TITLE_SIGNAL")
 def test_dual_provider_identity(self):
  with tempfile.TemporaryDirectory() as td:
   db=harvest_qgp.connect(pathlib.Path(td))
   openalex={"id":"https://openalex.org/W1","doi":"https://doi.org/10.1234/xyz",
            "display_name":"QGP Temperature","publication_date":"2025-04-13","publication_year":2025}
   inspire={"id":"123","metadata":{"titles":[{"title":"QGP Temperature"}],
             "dois":[{"value":"10.1234/xyz"}],"earliest_date":"2024-12-13",
             "publication_info":[{"year":2025}]}}
   with db:
    harvest_qgp.add(db,"openalex","test",openalex,"2026-11-08")
    harvest_qgp.add(db,"inspire","test",inspire,"2026-11-08")
   self.assertEqual(db.execute("select count(*) from works").fetchone()[0],1)
   self.assertEqual(db.execute("select count(*) from observations").fetchone()[0],2)
   db.close()
 def test_fixed_page_size(self):
  with tempfile.TemporaryDirectory() as td:
   script=pathlib.Path(harvest_qgp.__file__).resolve()
   opts=[sys.executable,str(script),"--out",td,"--years","2026",
         "--max-requests","0","--min-free-gb","0"]
   one=subprocess.run(opts,text=True,capture_output=True,timeout=12)
   self.assertEqual(one.returncode,0,one.stderr)
   stored=json.loads((pathlib.Path(td)/"collection_config.json").read_text())
   self.assertEqual(stored["per_page"],40)
   two=subprocess.run(opts+["--per-page","100"],text=True,capture_output=True,timeout=12)
   self.assertNotEqual(two.returncode,0)
   self.assertIn("different per-page size",two.stderr)
if __name__=="__main__":unittest.main(verbosity=2)
