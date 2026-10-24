from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest

from accounting import CrossKindModel, EvidenceClass, QuantityKind, WorkAccountingError, WorkQuantity
from session import AppliedWorkSession, EvidenceArtifact, verify_manifest


COMMIT = "a" * 40
ARTIFACT_SHA = "b" * 64


def evidence() -> EvidenceArtifact:
    return EvidenceArtifact(
        evidence_id="meter-run-001",
        sha256=ARTIFACT_SHA,
        uri="file:///evidence/meter-run-001.json",
        captured_at="2026-10-20T23:40:00-04:00",
        collector="worldshepherd-meter-agent",
        media_type="application/json",
    )


def measured_energy() -> WorkQuantity:
    return WorkQuantity(
        quantity_id="energy-001",
        kind=QuantityKind.ENERGY,
        value=Decimal("1.25"),
        unit="kWh",
        basis="electrical_input_energy",
        provenance="evidence:meter-run-001",
        evidence_class=EvidenceClass.MEASURED,
        uncertainty=Decimal("0.02"),
        scope="qcrypto-ci",
        time_window="2026-10-20T23:40:00-04:00/2026-10-20T23:45:00-04:00",
    )


def benchmarked_compute() -> WorkQuantity:
    return WorkQuantity(
        quantity_id="compute-001",
        kind=QuantityKind.COMPUTE,
        value=Decimal("8"),
        unit="Top",
        basis="floating_point_operation",
        provenance="evidence:meter-run-001",
        evidence_class=EvidenceClass.BENCHMARKED,
        uncertainty=Decimal("0.1"),
        scope="qcrypto-ci",
    )


def session() -> AppliedWorkSession:
    return AppliedWorkSession(
        session_id="WS-WORK-20261020-001",
        subject="QCRYPTO exact-head validation",
        source_commit=COMMIT,
        build_identity="github-actions:run-35000000000",
        collector="worldshepherd-applied-work",
        started_at="2026-10-20T23:39:00-04:00",
    )


class AppliedWorkSessionTests(unittest.TestCase):
    def test_measured_quantity_requires_hashed_evidence(self):
        item = session()
        with self.assertRaisesRegex(WorkAccountingError, "hashed evidence artifact"):
            item.add_quantity(measured_energy())

    def test_benchmarked_model_requires_hashed_evidence(self):
        item = session()
        model = CrossKindModel(
            model_id="compute-energy",
            input_kind=QuantityKind.COMPUTE,
            input_unit="Top",
            input_basis="floating_point_operation",
            output_kind=QuantityKind.ENERGY,
            output_unit="kWh",
            output_basis="electrical_input_energy",
            output_per_input=Decimal("0.1"),
            provenance="paired benchmark",
            evidence_class=EvidenceClass.BENCHMARKED,
        )
        with self.assertRaisesRegex(WorkAccountingError, "hashed evidence artifact"):
            item.add_model(model)

    def test_session_seal_and_verification_pass(self):
        item = session()
        item.add_evidence(evidence())
        item.add_quantity(measured_energy(), evidence_ids=("meter-run-001",))
        item.add_quantity(benchmarked_compute(), evidence_ids=("meter-run-001",))
        seal = item.seal(ended_at="2026-10-20T23:46:00-04:00")
        self.assertEqual(len(seal), 64)

        manifest = item.manifest()
        result = verify_manifest(manifest)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["evidence_count"], 1)
        self.assertEqual(result["recomputed_seal_digest"], seal)

    def test_derived_quantity_preserves_session_lineage(self):
        item = session()
        item.add_evidence(evidence())
        item.add_quantity(benchmarked_compute(), evidence_ids=("meter-run-001",))
        item.add_model(
            CrossKindModel(
                model_id="compute-energy",
                input_kind=QuantityKind.COMPUTE,
                input_unit="Top",
                input_basis="floating_point_operation",
                output_kind=QuantityKind.ENERGY,
                output_unit="kWh",
                output_basis="electrical_input_energy",
                output_per_input=Decimal("0.1"),
                provenance="evidence:meter-run-001",
                evidence_class=EvidenceClass.MEASURED,
                uncertainty_fraction=Decimal("0.02"),
            ),
            evidence_ids=("meter-run-001",),
        )
        derived = item.derive("compute-001", "compute-energy", output_id="energy-derived")
        self.assertEqual(derived.value, Decimal("0.8"))
        self.assertEqual(derived.evidence_class, EvidenceClass.BENCHMARKED)
        self.assertEqual(
            item.ledger.lineage("energy-derived"),
            ("energy-derived", "compute-energy", "compute-001"),
        )
        item.seal(ended_at="2026-10-20T23:46:00-04:00")
        self.assertTrue(verify_manifest(item.manifest())["ok"])

    def test_payload_tamper_is_detected(self):
        item = session()
        item.add_evidence(evidence())
        item.add_quantity(measured_energy(), evidence_ids=("meter-run-001",))
        item.seal(ended_at="2026-10-20T23:46:00-04:00")
        tampered = deepcopy(item.manifest())
        quantity_event = next(
            event for event in tampered["events"] if event["event_type"] == "QUANTITY_RECORDED"
        )
        quantity_event["payload"]["quantity"]["value"] = "999"
        result = verify_manifest(tampered)
        self.assertFalse(result["ok"])
        self.assertTrue(any("payload hash mismatch" in reason for reason in result["reasons"]))

    def test_event_reorder_is_detected(self):
        item = session()
        item.add_evidence(evidence())
        item.add_quantity(measured_energy(), evidence_ids=("meter-run-001",))
        item.seal(ended_at="2026-10-20T23:46:00-04:00")
        tampered = deepcopy(item.manifest())
        tampered["events"][0], tampered["events"][1] = tampered["events"][1], tampered["events"][0]
        result = verify_manifest(tampered)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("sequence mismatch" in reason or "predecessor mismatch" in reason for reason in result["reasons"])
        )

    def test_unknown_evidence_reference_is_rejected(self):
        item = session()
        with self.assertRaisesRegex(WorkAccountingError, "unknown evidence reference"):
            item.add_quantity(measured_energy(), evidence_ids=("missing",))

    def test_sealed_session_cannot_be_mutated(self):
        item = session()
        item.add_evidence(evidence())
        item.add_quantity(measured_energy(), evidence_ids=("meter-run-001",))
        item.seal(ended_at="2026-10-20T23:46:00-04:00")
        with self.assertRaisesRegex(WorkAccountingError, "immutable"):
            item.add_evidence(
                EvidenceArtifact(
                    evidence_id="extra",
                    sha256="c" * 64,
                    uri="file:///extra",
                    captured_at="2026-10-20T23:47:00-04:00",
                    collector="test",
                )
            )

    def test_source_commit_must_be_full_git_sha(self):
        with self.assertRaisesRegex(WorkAccountingError, "full 40-character"):
            AppliedWorkSession(
                session_id="bad",
                subject="bad",
                source_commit="abc123",
                build_identity="test",
                collector="test",
                started_at="2026-10-20T23:39:00-04:00",
            )

    def test_ended_at_cannot_precede_started_at(self):
        item = session()
        item.add_evidence(evidence())
        with self.assertRaisesRegex(WorkAccountingError, "cannot precede"):
            item.seal(ended_at="2026-10-20T23:38:00-04:00")


if __name__ == "__main__":
    unittest.main()
