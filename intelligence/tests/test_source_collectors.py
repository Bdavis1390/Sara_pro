from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
INTELLIGENCE = HERE.parents[1]
sys.path.insert(0, str(INTELLIGENCE))

import source_collectors as collectors


class CollectorTests(unittest.TestCase):
    @patch("source_collectors.fetch_json")
    def test_datagov_normalization(self, fetch_json):
        fetch_json.return_value = {
            "results": [
                {
                    "title": "Advanced Manufacturing Dataset",
                    "identifier": "dataset-123",
                    "dcat": {
                        "landingPage": "https://example.gov/dataset-123",
                        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
                    },
                }
            ]
        }
        records = collectors.datagov_search("advanced manufacturing", "secret-key", 5)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source_id, "WS-SRC-USADATA")
        self.assertEqual(records[0].upstream_id, "dataset-123")
        self.assertNotIn("secret-key", records[0].canonical_url)

    @patch("source_collectors.fetch_json")
    def test_loc_normalization(self, fetch_json):
        fetch_json.return_value = {
            "results": [
                {
                    "id": "http://www.loc.gov/item/test/",
                    "url": "https://www.loc.gov/item/test/",
                    "title": "Historic engineering drawing",
                    "rights": ["Rights status varies by item"],
                }
            ]
        }
        records = collectors.loc_search("engineering drawing", 5)
        self.assertEqual(records[0].source_id, "WS-SRC-LOC")
        self.assertIn("Rights status", records[0].rights_label)

    @patch("source_collectors.fetch_json")
    def test_smithsonian_normalization_does_not_store_api_key(self, fetch_json):
        fetch_json.return_value = {
            "response": {
                "rows": [
                    {
                        "id": "edanmdm-test",
                        "title": "Test object",
                        "content": {
                            "descriptiveNonRepeating": {
                                "record_link": "https://www.si.edu/object/test",
                                "metadata_usage": {"access": "CC0"},
                            }
                        },
                    }
                ]
            }
        }
        records = collectors.smithsonian_search("aerospace", "super-secret", 5)
        self.assertEqual(records[0].source_id, "WS-SRC-SMITHSONIAN")
        self.assertEqual(records[0].rights_label, "CC0")
        self.assertNotIn("super-secret", records[0].canonical_url)
        self.assertNotIn("super-secret", records[0].query_text)

    @patch("source_collectors.fetch_json")
    def test_bls_registration_key_not_stored(self, fetch_json):
        fetch_json.return_value = {
            "Results": {
                "series": [
                    {"seriesID": "CES0000000001", "data": [{"year": "2026", "value": "1"}]}
                ]
            }
        }
        records = collectors.bls_series(
            ["CES0000000001"], 2025, 2026, "registration-secret"
        )
        self.assertEqual(records[0].upstream_id, "CES0000000001")
        self.assertNotIn("registration-secret", records[0].query_text)
        self.assertNotIn("registration-secret", records[0].canonical_url)

    @patch("source_collectors.fetch_json")
    def test_census_api_key_not_stored(self, fetch_json):
        fetch_json.return_value = [["NAME", "B01003_001E", "state"], ["North Carolina", "11000000", "37"]]
        records = collectors.census_query(
            2024, "acs/acs5", "NAME,B01003_001E", "state:37", "census-secret"
        )
        record = records[0]
        self.assertEqual(record.source_id, "WS-SRC-CENSUS")
        self.assertNotIn("census-secret", record.query_text)
        self.assertNotIn("census-secret", record.canonical_url)

    @patch("source_collectors.fetch_json")
    def test_nara_is_live_query_adapter(self, fetch_json):
        fetch_json.return_value = {"body": {"hits": {"hits": []}}}
        result = collectors.nara_live_search("advanced propulsion", "nara-secret", 5)
        self.assertIn("body", result)
        fetch_json.assert_called_once()


if __name__ == "__main__":
    unittest.main()
