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

    def test_explicit_compute_to_energy_model_preserves_lineage_and_uncertainty(self):
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
                uncertainty=Decimal("0.2"),
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
                uncertainty_fraction=Decimal("0.04"),
                conditions=("accelerator-A", "benchmark workload A"),
            )
        )
        energy = ledger.derive("compute-1", "energy-per-compute-A", output_id="energy-1")
        self.assertEqual(energy.value, Decimal("2.50"))
        self.assertEqual(energy.unit, "kWh")
        self.assertEqual(energy.evidence_class, EvidenceClass.BENCHMARKED)
        # 0.2 Top input uncertainty * 0.25 kWh/Top + 4% of 2.5 kWh.
        self.assertEqual(energy.uncertainty, Decimal("0.1500"))
        self.assertEqual(
            ledger.lineage("energy-1"),
            ("energy-1", "energy-per-compute-A", "compute-1"),
        )

    def test_compute_to_energy_to_cost_chain_preserves_weakest_evidence(self):
        ledger = AppliedWorkLedger()
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="compute",
                kind=QuantityKind.COMPUTE,
                value="40",
                unit="Top",
                basis="floating_point_operation",
                provenance="benchmark counter",
                evidence_class=EvidenceClass.BENCHMARKED,
            )
        )
        ledger.add_model(
            CrossKindModel(
                model_id="compute-energy",
                input_kind=QuantityKind.COMPUTE,
                input_unit="Top",
                input_basis="floating_point_operation",
                output_kind=QuantityKind.ENERGY,
                output_unit="kWh",
                output_basis="electrical_input_energy",
                output_per_input="0.1",
                provenance="paired power meter benchmark",
                evidence_class=EvidenceClass.MEASURED,
            )
        )
        ledger.add_model(
            CrossKindModel(
                model_id="energy-cost",
                input_kind=QuantityKind.ENERGY,
                input_unit="kWh",
                input_basis="electrical_input_energy",
                output_kind=QuantityKind.COST,
                output_unit="USD",
                output_basis="electricity_cost",
                output_per_input="0.12",
                provenance="example tariff assumption",
                evidence_class=EvidenceClass.ASSUMPTION,
            )
        )
        energy = ledger.derive("compute", "compute-energy", output_id="energy")
        cost = ledger.derive("energy", "energy-cost", output_id="cost")
        self.assertEqual(energy.value, Decimal("4.0"))
        self.assertEqual(cost.value, Decimal("0.480"))
        self.assertEqual(cost.evidence_class, EvidenceClass.ASSUMPTION)
        self.assertEqual(
            ledger.lineage("cost"),
            ("cost", "energy-cost", "energy", "compute-energy", "compute"),
        )

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

    def test_same_kind_different_basis_requires_explicit_model(self):
        gpu = WorkQuantity(
            quantity_id="gpu-time",
            kind=QuantityKind.RESOURCE_TIME,
            value="2",
            unit="resource-h",
            basis="H100_GPU",
            provenance="scheduler",
            evidence_class=EvidenceClass.MEASURED,
        )
        model = CrossKindModel(
            model_id="gpu-to-cpu-equivalent",
            input_kind=QuantityKind.RESOURCE_TIME,
            input_unit="resource-h",
            input_basis="H100_GPU",
            output_kind=QuantityKind.RESOURCE_TIME,
            output_unit="resource-h",
            output_basis="CPU_core",
            output_per_input="60",
            provenance="workload-specific comparative benchmark",
            evidence_class=EvidenceClass.BENCHMARKED,
            conditions=("workload-X",),
        )
        cpu = model.apply(gpu, output_id="cpu-equivalent")
        self.assertEqual(cpu.value, Decimal("120"))
        self.assertEqual(cpu.basis, "CPU_core")
        self.assertEqual(cpu.evidence_class, EvidenceClass.BENCHMARKED)

    def test_same_kind_same_basis_transform_is_rejected(self):
        with self.assertRaisesRegex(WorkAccountingError, "same-kind/same-basis"):
            CrossKindModel(
                model_id="bad-model",
                input_kind=QuantityKind.ENERGY,
                input_unit="kWh",
                input_basis="electrical_input_energy",
                output_kind=QuantityKind.ENERGY,
                output_unit="J",
                output_basis="electrical_input_energy",
                output_per_input="3600000",
                provenance="should be a unit conversion",
                evidence_class=EvidenceClass.MEASURED,
            )

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

    def test_aggregation_rejects_duplicate_quantity_id(self):
        ledger = AppliedWorkLedger()
        ledger.add_quantity(
            WorkQuantity(
                quantity_id="energy",
                kind=QuantityKind.ENERGY,
                value="1",
                unit="kWh",
                basis="electrical_input_energy",
                provenance="meter",
                evidence_class=EvidenceClass.MEASURED,
            )
        )
        with self.assertRaisesRegex(WorkAccountingError, "more than once"):
            ledger.aggregate(
                ["energy", "energy"],
                target_unit="kWh",
                output_id="double-counted",
                provenance="invalid double count",
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
                uncertainty="0.08",
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
                uncertainty="0.2",
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
        # Conservative relative uncertainty: 0.08/4 + 0.2/20 = 0.03.
        self.assertEqual(metric.uncertainty_fraction, Decimal("0.03"))

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
