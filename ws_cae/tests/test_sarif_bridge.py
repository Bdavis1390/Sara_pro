import unittest
from pathlib import Path

from ws_cae.sarif_cdx_cli import run

ROOT = Path(__file__).resolve().parents[2]


class SarifBridgeTests(unittest.TestCase):
    def test_reference_path_exports_sarif_210(self):
        doc = run(ROOT / "ws_cae/examples/system_stablecoin.json")
        self.assertEqual(doc["version"], "2.1.0")
        self.assertTrue(doc["$schema"].endswith("sarif-schema-2.1.0.json"))
        self.assertEqual(doc["runs"][0]["tool"]["driver"]["name"], "WS-CAE")

    def test_critical_weak_dependency_becomes_result(self):
        doc = run(ROOT / "ws_cae/examples/system_bridged_asset.json")
        results = doc["runs"][0]["results"]
        self.assertTrue(results)
        self.assertTrue(any(r["ruleId"] == "WSCAE001" for r in results))


if __name__ == "__main__":
    unittest.main()
