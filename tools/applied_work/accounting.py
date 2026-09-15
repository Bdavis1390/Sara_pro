from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Iterable


class WorkAccountingError(ValueError):
    """Raised when work quantities or transformations violate accounting rules."""


class QuantityKind(str, Enum):
    COMPUTE = "COMPUTE"
    ENERGY = "ENERGY"
    DURATION = "DURATION"
    RESOURCE_TIME = "RESOURCE_TIME"
    LABOR_TIME = "LABOR_TIME"
    DATA = "DATA"
    COST = "COST"
    MASS = "MASS"
    OUTPUT = "OUTPUT"
    EMISSIONS = "EMISSIONS"
    QUALITY = "QUALITY"


class EvidenceClass(str, Enum):
    ASSUMPTION = "ASSUMPTION"
    ESTIMATED = "ESTIMATED"
    SIMULATED = "SIMULATED"
    BENCHMARKED = "BENCHMARKED"
    MEASURED = "MEASURED"


_EVIDENCE_RANK = {
    EvidenceClass.ASSUMPTION: 1,
    EvidenceClass.ESTIMATED: 2,
    EvidenceClass.SIMULATED: 2,
    EvidenceClass.BENCHMARKED: 3,
    EvidenceClass.MEASURED: 4,
}


@dataclass(frozen=True)
class UnitSpec:
    symbol: str
    kind: QuantityKind
    factor_to_base: Decimal
    base_symbol: str


_UNIT_SPECS: dict[str, UnitSpec] = {}


def _unit(symbol: str, kind: QuantityKind, factor: str, base: str) -> None:
    _UNIT_SPECS[symbol] = UnitSpec(symbol, kind, Decimal(factor), base)


# Compute operations. The semantic operation type remains in WorkQuantity.basis,
# so floating-point operations are not silently equated with integer ops, tokens,
# inferences, or domain-specific work units.
for symbol, factor in (
    ("op", "1"),
    ("kop", "1e3"),
    ("Mop", "1e6"),
    ("Gop", "1e9"),
    ("Top", "1e12"),
    ("Pop", "1e15"),
):
    _unit(symbol, QuantityKind.COMPUTE, factor, "op")

# Energy. NIST SP 811 gives 1 kWh = 3.6e6 J.
for symbol, factor in (
    ("J", "1"),
    ("kJ", "1e3"),
    ("MJ", "1e6"),
    ("Wh", "3600"),
    ("kWh", "3.6e6"),
    ("MWh", "3.6e9"),
):
    _unit(symbol, QuantityKind.ENERGY, factor, "J")

for symbol, factor in (("s", "1"), ("min", "60"), ("h", "3600")):
    _unit(symbol, QuantityKind.DURATION, factor, "s")

# Resource-time and labor-time are deliberately separate from wall-clock duration.
# Basis identifies the resource type (e.g. H100 GPU, CPU core, technician).
for symbol, factor in (("resource-s", "1"), ("resource-min", "60"), ("resource-h", "3600")):
    _unit(symbol, QuantityKind.RESOURCE_TIME, factor, "resource-s")
for symbol, factor in (("person-s", "1"), ("person-min", "60"), ("person-h", "3600")):
    _unit(symbol, QuantityKind.LABOR_TIME, factor, "person-s")

for symbol, factor in (
    ("B", "1"),
    ("kB", "1e3"),
    ("MB", "1e6"),
    ("GB", "1e9"),
    ("TB", "1e12"),
    ("KiB", "1024"),
    ("MiB", "1048576"),
    ("GiB", "1073741824"),
):
    _unit(symbol, QuantityKind.DATA, factor, "B")

_unit("USD", QuantityKind.COST, "1", "USD")
for symbol, factor in (("g", "1e-3"), ("kg", "1"), ("t", "1e3")):
    _unit(symbol, QuantityKind.MASS, factor, "kg")
_unit("count", QuantityKind.OUTPUT, "1", "count")
for symbol, factor in (("gCO2e", "1e-3"), ("kgCO2e", "1"), ("tCO2e", "1e3")):
    _unit(symbol, QuantityKind.EMISSIONS, factor, "kgCO2e")
_unit("ratio", QuantityKind.QUALITY, "1", "ratio")


def _decimal(value: Decimal | int | float | str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise WorkAccountingError("quantity value must be numeric") from exc
    if not result.is_finite():
        raise WorkAccountingError("quantity value must be finite")
    return result


def _weakest_evidence(*classes: EvidenceClass) -> EvidenceClass:
    if not classes:
        raise WorkAccountingError("at least one evidence class is required")
    return min(classes, key=lambda item: _EVIDENCE_RANK[item])


@dataclass(frozen=True)
class WorkQuantity:
    quantity_id: str
    kind: QuantityKind
    value: Decimal
    unit: str
    basis: str
    provenance: str
    evidence_class: EvidenceClass
    uncertainty: Decimal | None = None
    scope: str = ""
    time_window: str = ""

    def __post_init__(self) -> None:
        value = _decimal(self.value)
        if value < 0:
            raise WorkAccountingError("work quantity values cannot be negative")
        object.__setattr__(self, "value", value)
        if not self.quantity_id.strip():
            raise WorkAccountingError("quantity_id is required")
        if not self.basis.strip():
            raise WorkAccountingError("basis is required")
        if not self.provenance.strip():
            raise WorkAccountingError("provenance is required")
        spec = _UNIT_SPECS.get(self.unit)
        if spec is None:
            raise WorkAccountingError(f"unsupported unit: {self.unit}")
        if spec.kind != self.kind:
            raise WorkAccountingError(
                f"unit {self.unit} belongs to {spec.kind.value}, not {self.kind.value}"
            )
        if self.uncertainty is not None:
            uncertainty = _decimal(self.uncertainty)
            if uncertainty < 0:
                raise WorkAccountingError("uncertainty cannot be negative")
            object.__setattr__(self, "uncertainty", uncertainty)

    def converted(self, target_unit: str) -> "WorkQuantity":
        """Convert units only within the same quantity kind and semantic basis."""
        source = _UNIT_SPECS[self.unit]
        target = _UNIT_SPECS.get(target_unit)
        if target is None:
            raise WorkAccountingError(f"unsupported target unit: {target_unit}")
        if target.kind != self.kind or target.base_symbol != source.base_symbol:
            raise WorkAccountingError(
                "implicit cross-kind conversion is prohibited; use an explicit CrossKindModel"
            )
        base_value = self.value * source.factor_to_base
        converted_value = base_value / target.factor_to_base
        converted_uncertainty = None
        if self.uncertainty is not None:
            converted_uncertainty = (
                self.uncertainty * source.factor_to_base / target.factor_to_base
            )
        return replace(
            self,
            value=converted_value,
            unit=target_unit,
            uncertainty=converted_uncertainty,
        )


@dataclass(frozen=True)
class CrossKindModel:
    """Explicit relation between unlike work quantities.

    `output_per_input` means `output_unit` per `input_unit` for the named semantic
    bases under the recorded conditions. This is a model, not a unit conversion.
    """

    model_id: str
    input_kind: QuantityKind
    input_unit: str
    input_basis: str
    output_kind: QuantityKind
    output_unit: str
    output_basis: str
    output_per_input: Decimal
    provenance: str
    evidence_class: EvidenceClass
    assumptions: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    model_version: str = "1"
    uncertainty_fraction: Decimal | None = None

    def __post_init__(self) -> None:
        rate = _decimal(self.output_per_input)
        if rate < 0:
            raise WorkAccountingError("cross-kind rate cannot be negative")
        object.__setattr__(self, "output_per_input", rate)
        if not self.model_id.strip() or not self.provenance.strip():
            raise WorkAccountingError("model_id and provenance are required")
        if not self.input_basis.strip() or not self.output_basis.strip():
            raise WorkAccountingError("input/output basis are required")
        input_spec = _UNIT_SPECS.get(self.input_unit)
        output_spec = _UNIT_SPECS.get(self.output_unit)
        if input_spec is None or input_spec.kind != self.input_kind:
            raise WorkAccountingError("input unit does not match input quantity kind")
        if output_spec is None or output_spec.kind != self.output_kind:
            raise WorkAccountingError("output unit does not match output quantity kind")
        if self.input_kind == self.output_kind:
            raise WorkAccountingError(
                "CrossKindModel is for unlike quantity kinds; use unit conversion for same-kind quantities"
            )
        if self.uncertainty_fraction is not None:
            fraction = _decimal(self.uncertainty_fraction)
            if fraction < 0:
                raise WorkAccountingError("uncertainty_fraction cannot be negative")
            object.__setattr__(self, "uncertainty_fraction", fraction)

    def apply(self, quantity: WorkQuantity, *, output_id: str) -> WorkQuantity:
        if quantity.kind != self.input_kind or quantity.basis != self.input_basis:
            raise WorkAccountingError(
                "quantity does not match the transform input kind and semantic basis"
            )
        normalized = quantity.converted(self.input_unit)
        output_value = normalized.value * self.output_per_input
        uncertainty = None
        if self.uncertainty_fraction is not None:
            uncertainty = output_value * self.uncertainty_fraction
        evidence = _weakest_evidence(quantity.evidence_class, self.evidence_class)
        return WorkQuantity(
            quantity_id=output_id,
            kind=self.output_kind,
            value=output_value,
            unit=self.output_unit,
            basis=self.output_basis,
            provenance=(
                f"derived from {quantity.quantity_id} via model {self.model_id} "
                f"v{self.model_version}; model provenance: {self.provenance}"
            ),
            evidence_class=evidence,
            uncertainty=uncertainty,
            scope=quantity.scope,
            time_window=quantity.time_window,
        )


@dataclass(frozen=True)
class DerivedMetric:
    metric_id: str
    numerator_quantity_id: str
    denominator_quantity_id: str
    value: Decimal
    unit: str
    provenance: str
    evidence_class: EvidenceClass


@dataclass
class AppliedWorkLedger:
    quantities: dict[str, WorkQuantity] = field(default_factory=dict)
    models: dict[str, CrossKindModel] = field(default_factory=dict)
    derivations: dict[str, tuple[str, str]] = field(default_factory=dict)

    def add_quantity(self, quantity: WorkQuantity) -> None:
        if quantity.quantity_id in self.quantities:
            raise WorkAccountingError(f"duplicate quantity_id: {quantity.quantity_id}")
        self.quantities[quantity.quantity_id] = quantity

    def add_model(self, model: CrossKindModel) -> None:
        if model.model_id in self.models:
            raise WorkAccountingError(f"duplicate model_id: {model.model_id}")
        self.models[model.model_id] = model

    def derive(self, input_quantity_id: str, model_id: str, *, output_id: str) -> WorkQuantity:
        if output_id in self.quantities:
            raise WorkAccountingError(f"duplicate output quantity_id: {output_id}")
        try:
            source = self.quantities[input_quantity_id]
            model = self.models[model_id]
        except KeyError as exc:
            raise WorkAccountingError(f"unknown ledger reference: {exc.args[0]}") from exc
        result = model.apply(source, output_id=output_id)
        self.quantities[output_id] = result
        self.derivations[output_id] = (input_quantity_id, model_id)
        return result

    def aggregate(
        self,
        quantity_ids: Iterable[str],
        *,
        target_unit: str,
        output_id: str,
        provenance: str,
    ) -> WorkQuantity:
        items = [self.quantities[item] for item in quantity_ids]
        if not items:
            raise WorkAccountingError("at least one quantity is required for aggregation")
        first = items[0]
        if any(item.kind != first.kind or item.basis != first.basis for item in items):
            raise WorkAccountingError(
                "aggregation requires the same quantity kind and semantic basis"
            )
        converted = [item.converted(target_unit) for item in items]
        evidence = _weakest_evidence(*(item.evidence_class for item in converted))
        result = WorkQuantity(
            quantity_id=output_id,
            kind=first.kind,
            value=sum((item.value for item in converted), Decimal("0")),
            unit=target_unit,
            basis=first.basis,
            provenance=provenance,
            evidence_class=evidence,
            scope=first.scope,
            time_window=first.time_window,
        )
        self.add_quantity(result)
        return result

    def intensity(
        self,
        numerator_id: str,
        denominator_id: str,
        *,
        metric_id: str,
        numerator_unit: str,
        denominator_unit: str,
        provenance: str,
    ) -> DerivedMetric:
        numerator = self.quantities[numerator_id].converted(numerator_unit)
        denominator = self.quantities[denominator_id].converted(denominator_unit)
        if denominator.value == 0:
            raise WorkAccountingError("intensity denominator cannot be zero")
        return DerivedMetric(
            metric_id=metric_id,
            numerator_quantity_id=numerator_id,
            denominator_quantity_id=denominator_id,
            value=numerator.value / denominator.value,
            unit=f"{numerator_unit}/{denominator_unit}",
            provenance=provenance,
            evidence_class=_weakest_evidence(
                numerator.evidence_class,
                denominator.evidence_class,
            ),
        )

    def vector(self) -> dict[str, dict[str, str]]:
        """Return native quantities without pretending they share one scalar unit."""
        return {
            key: {
                "kind": value.kind.value,
                "value": str(value.value),
                "unit": value.unit,
                "basis": value.basis,
                "evidence_class": value.evidence_class.value,
                "provenance": value.provenance,
            }
            for key, value in sorted(self.quantities.items())
        }
