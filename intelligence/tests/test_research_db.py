from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
INTELLIGENCE = HERE.parents[1]
sys.path.insert(0, str(INTELLIGENCE))

from research_db import DEFAULT_REGISTRY, ResearchDB, ResearchRecord


class ResearchDBTests(unittest.TestCase):
    def test_registry_load_and_nara_no_persistence_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "research.sqlite3"
            with ResearchDB(db_path) as db:
                count = db.load_registry(DEFAULT_REGISTRY)
                self.assertGreaterEqual(count, 16)
                nara = db.source("WS-SRC-NARA")
                self.assertEqual(nara["collector_allowed"], 1)
                self.assertEqual(nara["persistence_allowed"], 0)

                record = ResearchRecord(
                    source_id="WS-SRC-NARA",
                    upstream_id="123",
                    title="live result",
                    canonical_url="https://catalog.archives.gov/id/123",
                    query_text="test",
                    observed_at="2026-08-09T00:00:00+00:00",
                    payload={"record": 123},
                    validation_label="live only",
                )
                with self.assertRaises(PermissionError):
                    db.ingest(record)

    def test_ingest_is_hashed_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "research.sqlite3"
            with ResearchDB(db_path) as db:
                db.load_registry(DEFAULT_REGISTRY)
                record = ResearchRecord(
                    source_id="WS-SRC-LOC",
                    upstream_id="loc-1",
                    title="Example LOC record",
                    canonical_url="https://www.loc.gov/item/example/",
                    query_text="example",
                    observed_at="2026-08-09T00:00:00+00:00",
                    payload={"title": "Example LOC record", "id": "loc-1"},
                    validation_label="Official collection metadata",
                )
                first_id, first_inserted = db.ingest(record)
                second_id, second_inserted = db.ingest(record)
                self.assertTrue(first_inserted)
                self.assertFalse(second_inserted)
                self.assertEqual(first_id, second_id)
                stats = db.stats()
                self.assertEqual(stats["records"], 1)

                row = db.connection.execute(
                    "SELECT payload_sha256, payload_json FROM records WHERE id = ?",
                    (first_id,),
                ).fetchone()
                self.assertEqual(len(row["payload_sha256"]), 64)
                self.assertEqual(json.loads(row["payload_json"])["id"], "loc-1")

    def test_disabled_source_cannot_be_automatically_ingested(self):
        with tempfile.TemporaryDirectory() as temp:
            with ResearchDB(Path(temp) / "research.sqlite3") as db:
                db.load_registry(DEFAULT_REGISTRY)
                record = ResearchRecord(
                    source_id="WS-SRC-DNB-HOOVERS",
                    upstream_id="company",
                    title="Licensed company record",
                    canonical_url="https://www.dnb.com/",
                    query_text="company",
                    observed_at="2026-08-09T00:00:00+00:00",
                    payload={"licensed": True},
                    validation_label="license required",
                )
                with self.assertRaises(PermissionError):
                    db.ingest(record)


if __name__ == "__main__":
    unittest.main()
