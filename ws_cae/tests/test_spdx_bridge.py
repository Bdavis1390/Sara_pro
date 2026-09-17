import unittest
from pathlib import Path

from ws_cae.spdx_cdx_cli import run

ROOT = Path(__file__).resolve().parents[2]


class SpdxBridgeTests(unittest.TestCase):
    def test_reference_path_exports_spdx_301(self):
        doc = run(ROOT / "ws_cae/examples/system_stablecoin.json")
        self.assertEqual(doc["@context"], "https://spdx.org/rdf/3.0.1/spdx-context.jsonld")
        types = {item["type"] for item in doc["@graph"]}
        self.assertIn("SpdxDocument", types)
        self.assertIn("software_Sbom", types)
        self.assertIn("Relationship", types)

    def test_ws_cae_properties_are_preserved(self):
        doc = run(ROOT / "ws_cae/examples/system_native_coin.json")
        packages = [x for x in doc["@graph"] if x["type"] == "software_Package"]
        flattened = str(packages)
        self.assertIn("ws-cae:readiness-state", flattened)
        self.assertIn("ws-cae:critical", flattened)


if __name__ == "__main__":
    unittest.main()
