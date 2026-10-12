import unittest
from pathlib import Path

from ws_cae.cloudevents_cdx_cli import run

ROOT = Path(__file__).resolve().parents[2]


class CloudEventsBridgeTests(unittest.TestCase):
    def test_reference_path_exports_cloudevent(self):
        event = run(ROOT / "ws_cae/examples/system_stablecoin.json")
        self.assertEqual(event["specversion"], "1.0")
        self.assertEqual(event["type"], "dev.worldshepherd.wscae.readiness.assessed")
        self.assertEqual(event["datacontenttype"], "application/json")
        self.assertIn("system_state", event["data"])

    def test_event_preserves_dependency_states(self):
        event = run(ROOT / "ws_cae/examples/system_bridged_asset.json")
        states = {item["readiness_state"] for item in event["data"]["components"]}
        self.assertIn("CLASSICAL_DEPENDENCY", states)


if __name__ == "__main__":
    unittest.main()
