import unittest
from evidence_dependency_integrity import (
    SemanticSnapshot,
    DerivedClaim,
    VersionCoverage,
    validate_claim,
    needs_semantic_snapshot,
    medical_dataset_skew,
    legal_publication_state,
    intelligence_revalidation,
    software_doc_state,
)

class EvidenceDependencyIntegrityTests(unittest.TestCase):
    def test_partial_version_needs_snapshot(self):
        s = SemanticSnapshot("NM_123.1", native_version="1", coverage=VersionCoverage.PARTIAL)
        self.assertTrue(needs_semantic_snapshot(s))

    def test_annotation_release_changes_fingerprint(self):
        a = SemanticSnapshot(
            "refseq",
            native_version="1",
            annotation_release="110",
            coverage=VersionCoverage.PARTIAL,
        )
        b = SemanticSnapshot(
            "refseq",
            native_version="1",
            annotation_release="111",
            coverage=VersionCoverage.PARTIAL,
        )
        claim = DerivedClaim("c", a.semantic_fingerprint(), "annotation-based claim", "science")
        self.assertTrue(validate_claim(b, claim).stale)

    def test_clinvar_web_file_cadence(self):
        self.assertEqual(
            medical_dataset_skew("2026-09-17", "2026-09-01"),
            "BULK_FILE_MAY_LAG_WEB_SURFACE",
        )

    def test_slip_opinion_is_revision_sensitive(self):
        self.assertEqual(
            legal_publication_state("slip opinion"),
            "REVISION_SENSITIVE",
        )

    def test_intelligence_assumption_change_forces_reassessment(self):
        self.assertEqual(
            intelligence_revalidation(False, True, False),
            "JUDGMENT_REQUIRES_REASSESSMENT",
        )

    def test_software_docs_bound_to_runtime(self):
        self.assertEqual(
            software_doc_state("2026-03-10", "2022-11-28"),
            "DOC_RUNTIME_VERSION_MISMATCH",
        )

if __name__ == "__main__":
    unittest.main()
