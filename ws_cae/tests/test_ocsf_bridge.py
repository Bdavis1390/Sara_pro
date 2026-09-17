import unittest
from pathlib import Path

from ws_cae.ocsf_cdx_cli import run

ROOT = Path(__file__).resolve().parents[2]


class OcsfBridgeTests(unittest.TestCase):
    def test_reference_path_exports_detection_finding(self):
        event = run(ROOT / "ws_cae/examples/system_stablecoin.json")
        self.assertEqual(event["category_uid"], 2)
        self.assertEqual(event["class_uid"], 2004)
        self.assertEqual(event["type_uid"], 200401)
        self.assertEqual(event["metadata"]["version"], "1.8.0")
        self.assertIn("uid", event["finding_info"])

    def test_weak_components_are_preserved_in_unmapped(self):
        event = run(ROOT / "ws_cae/examples/system_rollup_asset.json")
        blockers = event["unmapped"]["ws_cae_blocking_components"]
        self.assertTrue(blockers)


if __name__ == "__main__":
    unittest.main()
