import unittest
from pathlib import Path

from ws_cae.cyclonedx_cli import run

ROOT = Path(__file__).resolve().parents[2]


class CycloneDXExportTests(unittest.TestCase):
    def test_exports_cyclonedx_17_with_deterministic_serial(self):
        path = ROOT / "ws_cae/examples/system_stablecoin.json"
        first = run(path)
        second = run(path)
        self.assertEqual(first["bomFormat"], "CycloneDX")
        self.assertEqual(first["specVersion"], "1.7")
        self.assertEqual(first["serialNumber"], second["serialNumber"])
        self.assertTrue(first["serialNumber"].startswith("urn:uuid:"))

    def test_asset_depends_on_all_declared_components(self):
        bom = run(ROOT / "ws_cae/examples/system_bridged_asset.json")
        self.assertEqual(len(bom["dependencies"]), 1)
        self.assertEqual(
            len(bom["dependencies"][0]["dependsOn"]),
            len(bom["components"]),
        )

    def test_ws_cae_semantics_are_preserved_as_properties(self):
        bom = run(ROOT / "ws_cae/examples/system_exchange_balance.json")
        component = bom["components"][0]
        props = {item["name"]: item["value"] for item in component["properties"]}
        self.assertIn("ws-cae:role", props)
        self.assertIn("ws-cae:readiness-state", props)
        self.assertIn("ws-cae:critical", props)
        self.assertIn("ws-cae:evidence-documented", props)

    def test_metadata_preserves_weakest_link_result(self):
        bom = run(ROOT / "ws_cae/examples/system_stablecoin.json")
        props = {
            item["name"]: item["value"]
            for item in bom["metadata"]["component"]["properties"]
        }
        self.assertEqual(
            props["ws-cae:weakest-readiness-state"],
            "CLASSICAL_DEPENDENCY",
        )


if __name__ == "__main__":
    unittest.main()
