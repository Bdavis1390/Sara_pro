from decimal import Decimal
import unittest

from accounting import (
    AppliedWorkLedger,
    CrossKindModel,
    EvidenceClass,
    QuantityKind,
    WorkAccountingError,
    WorkQuantity,
)


class AppliedWorkAccountingTests(unittest.TestCase):
    def test_same_kind_energy_conversion_uses_exact_kwh_relation(self):
        energy = WorkQuantity(
            quantity_id="energy-1",
            kind=QuantityKind.ENERGY,
            value=Decimal("1"),
            unit="kWh",
            basis="electrical_input_energy",
            provenance="metered",
            evidence_class=EvidenceClass.MEASURED,
        )
        joules = energy.converted("J")
        self.assertEqual(joules.value, Decimal("3600000"))
        self.assertEqual(joules.basis, "electrical_input_energy")

    def test_compute_cannot_be_implicitly_converted_to_energy(self):
        compute = WorkQuantity(
            quantity_id="compute-1",
            kind=QuantityKind.COMPUTE,
            value=Decimal("10"),
            unit="Top",
            basis="floating_point_operation",
            provenance="benchmark counter",
            evidence_class=EvidenceClass.BENCHMARKED,
        )
        with self.assertRaisesRegex(WorkAccountingError, "implicit cross-kind conversion"):
            compute.converted("kWh")

    def test_explicit_compute_to_energy_model_preserves_lineage(self):
        ledger = AppliedWorkLedger()
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="compute-1",
                kind=QuantityKind.COMPUTE,
                value=Decimal("10"),
                unit="Top",
                basis="floating_point_operation",
                provenance="hardware benchmark run A",
                evidence_class=EvidenceClass.BENCHMARKED,
                scope="accelerator-A",
            )
        )
        ledger.add_model(
            CrossKindModel(
                model_id="energy-per-compute-A",
                input_kind=QuantityKind.COMPUTE,
                input_unit="Top",
                input_basis="floating_point_operation",
                output_kind=QuantityKind.ENERGY,
                output_unit="kWh",
                output_basis="electrical_input_energy",
                output_per_input=Decimal("0.25"),
                provenance="metered benchmark paired with compute counter",
                evidence_class=EvidenceClass.MEASURED,
                conditions=("accelerator-A", "benchmark workload A"),
            )
        )
        energy = ledger.derive("compute-1", "energy-per-compute-A", output_id="energy-1")
        self.assertEqual(energy.value, Decimal("2.50"))
        self.assertEqual(energy.unit, "kWh")
        self.assertEqual(energy.evidence_class, EvidenceClass.BENCHMARKED)
        self.assertIn("energy-per-compute-A", energy.provenance)

    def test_model_does_not_apply_to_wrong_compute_basis(self):
        quantity = WorkQuantity(
            quantity_id="compute-int-1",
            kind=QuantityKind.COMPUTE,
            value=Decimal("2"),
            unit="Top",
            basis="integer_operation",
            provenance="counter",
            evidence_class=EvidenceClass.MEASURED,
        )
        model = CrossKindModel(
            model_id="fp-energy-model",
            input_kind=QuantityKind.COMPUTE,
            input_unit="Top",
            input_basis="floating_point_operation",
            output_kind=QuantityKind.ENERGY,
            output_unit="kWh",
            output_basis="electrical_input_energy",
            output_per_input=Decimal("0.1"),
            provenance="measured on floating-point workload",
            evidence_class=EvidenceClass.MEASURED,
        )
        with self.assertRaisesRegex(WorkAccountingError, "semantic basis"):
            model.apply(quantity, output_id="bad-energy")

    def test_aggregation_rejects_different_semantic_bases(self):
        ledger = AppliedWorkLedger()
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="fp",
                kind=QuantityKind.COMPUTE,
                value=1,
                unit="Top",
                basis="floating_point_operation",
                provenance="counter A",
                evidence_class=EvidenceClass.MEASURED,
            )
        )
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="int",
                kind=QuantityKind.COMPUTE,
                value=1,
                unit="Top",
                basis="integer_operation",
                provenance="counter B",
                evidence_class=EvidenceClass.MEASURED,
            )
        )
        with self.assertRaisesRegex(WorkAccountingError, "same quantity kind and semantic basis"):
            ledger.aggregate(
                ["fp", "int"],
                target_unit="Top",
                output_id="invalid",
                provenance="invalid aggregation",
            )

    def test_intensity_is_a_derived_metric_not_a_unit_conversion(self):
        ledger = AppliedWorkLedger()
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="energy",
                kind=QuantityKind.ENERGY,
                value="4",
                unit="kWh",
                basis="electrical_input_energy",
                provenance="meter",
                evidence_class=EvidenceClass.MEASURED,
            )
        )
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="compute",
                kind=QuantityKind.COMPUTE,
                value="20",
                unit="Top",
                basis="floating_point_operation",
                provenance="counter",
                evidence_class=EvidenceClass.BENCHMARKED,
            )
        )
        metric = ledger.intensity(
            "energy",
            "compute",
            metric_id="energy-intensity",
            numerator_unit="kWh",
            denominator_unit="Top",
            provenance="paired run A",
        )
        self.assertEqual(metric.value, Decimal("0.2"))
        self.assertEqual(metric.unit, "kWh/Top")
        self.assertEqual(metric.evidence_class, EvidenceClass.BENCHMARKED)

    def test_resource_time_is_not_wall_clock_duration(self):
        resource_time = WorkQuantity(
            quantity_id="gpu-time",
            kind=QuantityKind.RESOURCE_TIME,
            value="8",
            unit="resource-h",
            basis="H100_GPU",
            provenance="scheduler accounting",
            evidence_class=EvidenceClass.MEASURED,
        )
        with self.assertRaisesRegex(WorkAccountingError, "implicit cross-kind conversion"):
            resource_time.converted("h")

    def test_vector_keeps_quantities_native(self):
        ledger = AppliedWorkLedger()
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="compute",
                kind=QuantityKind.COMPUTE,
                value="5",
                unit="Top",
                basis="floating_point_operation",
                provenance="counter",
                evidence_class=EvidenceClass.BENCHMARKED,
            )
        )
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="energy",
                kind=QuantityKind.ENERGY,
                value="1.2",
                unit="kWh",
                basis="electrical_input_energy",
                provenance="meter",
                evidence_class=EvidenceClass.MEASURED,
            )
        )
        vector = ledger.vector()
        self.assertEqual(vector["compute"]["unit"], "Top")
        self.assertEqual(vector["energy"]["unit"], "kWh")
        self.assertNotIn("total_work", vector)


if __name__ == "__main__":
    unittest.main()
