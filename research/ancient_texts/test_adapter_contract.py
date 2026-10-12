import unittest
from adapter_contract import (
    SourceRecord,
    canonical_reference,
    can_copy_layer,
)

class AdapterContractTests(unittest.TestCase):
    def test_open_transcription_is_ingestable(self):
        record = SourceRecord(
            "source",
            "id-1",
            "https://example.invalid/1",
            {"metadata": "OPEN_REUSE", "transcription": "OPEN_REUSE"},
            raw_transcription="abc",
        )
        self.assertEqual(
            canonical_reference(record)["diplomatic_transcription"],
            "abc",
        )

    def test_restricted_transcription_becomes_reference_only(self):
        record = SourceRecord(
            "source",
            "id-2",
            "https://example.invalid/2",
            {"metadata": "OPEN_REUSE", "transcription": "PERMISSION_REQUIRED"},
            raw_transcription="abc",
        )
        out = canonical_reference(record)
        self.assertIsNone(out["diplomatic_transcription"])
        self.assertTrue(out["transcription_reference_only"])

    def test_missing_rights_fail_closed(self):
        record = SourceRecord(
            "source",
            "id-3",
            "https://example.invalid/3",
            {"metadata": "OPEN_REUSE"},
            raw_transcription="abc",
        )
        self.assertFalse(can_copy_layer(record, "transcription"))

if __name__ == "__main__":
    unittest.main()
