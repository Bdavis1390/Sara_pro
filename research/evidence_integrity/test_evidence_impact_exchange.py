import unittest
from evidence_impact_exchange import (
    ChangeType,
    ImpactState,
    EvidenceChangeEvent,
    ImpactAssessment,
    initial_impact_assessments,
    prime_action,
    crossmark_status_to_change_type,
    w3c_prov_relation,
    vex_like_status,
)

class EvidenceImpactExchangeTests(unittest.TestCase):
    def test_initial_blast_radius_is_potentially_affected(self):
        event = EvidenceChangeEvent(
            "e1","source",ChangeType.CORRECTION,"a","b","source-ref"
        )
        out = initial_impact_assessments(event, ["c1","c2"])
        self.assertEqual(len(out), 2)
        self.assertTrue(all(x.state == ImpactState.POTENTIALLY_AFFECTED for x in out))

    def test_not_affected_requires_evidence(self):
        assessment = ImpactAssessment(
            "e1","c1",ImpactState.NOT_AFFECTED,"independent support"
        )
        with self.assertRaises(ValueError):
            assessment.validate()

    def test_revalidated_can_be_released(self):
        assessment = ImpactAssessment(
            "e1","c1",ImpactState.REVALIDATED,
            "recomputed against corrected source",
            evidence_refs=["run:123"],
        )
        self.assertEqual(prime_action(assessment), "ALLOW_WITH_AUDIT_TRAIL")

    def test_retraction_maps_to_prov_invalidation(self):
        self.assertEqual(
            w3c_prov_relation(ChangeType.RETRACTION),
            "prov:wasInvalidatedBy",
        )

    def test_crossmark_correction_maps(self):
        self.assertEqual(
            crossmark_status_to_change_type("Correction"),
            ChangeType.CORRECTION,
        )

    def test_vex_analogy(self):
        self.assertEqual(
            vex_like_status(ImpactState.NOT_AFFECTED),
            "not_affected",
        )

if __name__ == "__main__":
    unittest.main()
