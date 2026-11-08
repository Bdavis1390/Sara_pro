import copy
import unittest
from pathlib import Path

from ws_cae.continuity_catalog import build
from ws_cae.continuity_snapshot_scitt import build_snapshot_statement, verify_snapshot_statement

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
PATCHES = [
    EXAMPLES / "algorand.patch.json",
    EXAMPLES / "bitcoin-qsb.patch.json",
    EXAMPLES / "ethereum.patch.json",
    EXAMPLES / "sui.patch.json",
]


class ContinuitySnapshotScittTests(unittest.TestCase):
    def snapshot(self) -> dict:
        return build(PATCHES, version="1", as_of="2026-09-13")

    def test_four_chain_snapshot_statement_verifies(self):
        statement = build_snapshot_statement(
            self.snapshot(),
            "did:web:example.invalid",
            "2026-09-14T00:30:00Z",
        )
        self.assertEqual(statement["snapshot"]["manifest_count"], 4)
        self.assertEqual(statement["snapshot_id"], statement["snapshot"]["snapshot_id"])
        self.assertTrue(verify_snapshot_statement(statement))

    def test_manifest_order_is_normalized_by_catalog(self):
        left = build(PATCHES, version="1", as_of="2026-09-13")
        right = build(list(reversed(PATCHES)), version="1", as_of="2026-09-13")
        self.assertEqual(left, right)

    def test_tampered_snapshot_root_is_rejected(self):
        snapshot = self.snapshot()
        snapshot["snapshot_id"] = "sha256:" + "00" * 32
        with self.assertRaises(ValueError):
            build_snapshot_statement(snapshot, "did:web:example.invalid")

    def test_tampered_manifest_content_id_is_rejected(self):
        snapshot = self.snapshot()
        snapshot["manifests"][0]["content_id"] = "sha256:" + "00" * 32
        with self.assertRaises(ValueError):
            build_snapshot_statement(snapshot, "did:web:example.invalid")

    def test_invalid_manifest_state_is_rejected(self):
        snapshot = self.snapshot()
        snapshot["manifests"][0]["valid"] = False
        with self.assertRaises(ValueError):
            build_snapshot_statement(snapshot, "did:web:example.invalid")

    def test_tampered_statement_binding_fails_verification(self):
        statement = build_snapshot_statement(
            self.snapshot(),
            "did:web:example.invalid",
            "2026-09-14T00:30:00Z",
        )
        altered = copy.deepcopy(statement)
        altered["snapshot_id"] = "sha256:" + "00" * 32
        self.assertFalse(verify_snapshot_statement(altered))

    def test_timezone_less_observed_at_is_rejected(self):
        with self.assertRaises(ValueError):
            build_snapshot_statement(
                self.snapshot(),
                "did:web:example.invalid",
                "2026-09-14T00:30:00",
            )


if __name__ == "__main__":
    unittest.main()
