from __future__ import annotations

from enum import Enum
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


G9_PROTOCOL_SCHEMA = "WS-SDA-G9-BENCHMARK-PROTOCOL-V1"
G9_MEASUREMENT_SCHEMA = "WS-SDA-G9-MEASUREMENT-BUNDLE-V1"
G9_REPORT_SCHEMA = "WS-SDA-G9-BENCHMARK-REPORT-V1"
TEN_X_MAX_RATIO = 0.10


class SdaBenchmarkError(ValueError):
    pass


class MetricDirection(str, Enum):
    LOWER_IS_BETTER = "LOWER_IS_BETTER"
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"


class MetricClass(str, Enum):
    SECURITY = "SECURITY"
    UTILITY = "UTILITY"


class SecurityTreatment(str, Enum):
    RATIO_OR_ZERO_INVARIANT = "RATIO_OR_ZERO_INVARIANT"
    ZERO_INVARIANT = "ZERO_INVARIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SdaBenchmarkMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(pattern=r"^[a-z0-9_]{3,96}$")
    metric_class: MetricClass
    unit: str = Field(min_length=1, max_length=64)
    direction: MetricDirection
    mandatory: bool = True
    min_samples: int = Field(ge=1, le=1_000_000)
    security_treatment: SecurityTreatment = SecurityTreatment.NOT_APPLICABLE
    max_candidate_to_baseline_ratio: float | None = Field(default=None, gt=0.0)
    max_relative_regression: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_metric_semantics(self):
        if self.metric_class == MetricClass.SECURITY:
            if self.direction != MetricDirection.LOWER_IS_BETTER:
                raise ValueError("security metrics must be LOWER_IS_BETTER in G9 v1")
            if self.security_treatment == SecurityTreatment.NOT_APPLICABLE:
                raise ValueError("security metric requires an explicit security treatment")
            if self.security_treatment == SecurityTreatment.RATIO_OR_ZERO_INVARIANT:
                if self.max_candidate_to_baseline_ratio is None:
                    raise ValueError("ratio security metric requires a maximum ratio")
                if self.max_candidate_to_baseline_ratio > TEN_X_MAX_RATIO:
                    raise ValueError("10x security metric ratio must be <= 0.10")
            if self.max_relative_regression is not None:
                raise ValueError("security metrics do not use utility regression budgets")
        else:
            if self.security_treatment != SecurityTreatment.NOT_APPLICABLE:
                raise ValueError("utility metric cannot declare security treatment")
            if self.max_relative_regression is None:
                raise ValueError("utility metric requires max_relative_regression")
            if self.max_candidate_to_baseline_ratio is not None:
                raise ValueError("utility metric cannot declare a 10x security ratio")
        return self


class SdaBenchmarkProtocol(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[G9_PROTOCOL_SCHEMA] = G9_PROTOCOL_SCHEMA
    protocol_id: str = Field(min_length=1, max_length=128)
    g8_corpus_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    required_environment_id: str = Field(min_length=1, max_length=256)
    metrics: list[SdaBenchmarkMetric] = Field(min_length=1, max_length=128)
    claims_boundary: str = Field(min_length=1)

    @model_validator(mode="after")
    def unique_metrics_and_security_count(self):
        ids = [item.metric_id for item in self.metrics]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark protocol contains duplicate metric IDs")
        mandatory_security = [
            item
            for item in self.metrics
            if item.metric_class == MetricClass.SECURITY and item.mandatory
        ]
        if len(mandatory_security) < 10:
            raise ValueError("G9 v1 requires at least 10 mandatory security metrics")
        return self


class SdaMetricMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    unit: str = Field(min_length=1, max_length=64)
    value: float = Field(ge=0.0)
    sample_count: int = Field(ge=1)
    evidence_ref: str = Field(min_length=1, max_length=512)

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("measurement value must be finite")
        return value


class SdaBenchmarkMeasurementBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[G9_MEASUREMENT_SCHEMA] = G9_MEASUREMENT_SCHEMA
    bundle_id: str = Field(min_length=1, max_length=128)
    role: Literal["BASELINE", "CANDIDATE"]
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    environment_id: str = Field(min_length=1, max_length=256)
    workload_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    measurements: list[SdaMetricMeasurement] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def metric_ids_unique(self):
        ids = [item.metric_id for item in self.measurements]
        if len(ids) != len(set(ids)):
            raise ValueError("measurement bundle contains duplicate metric IDs")
        return self


class SdaMetricResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    metric_class: MetricClass
    mandatory: bool
    baseline_value: float
    candidate_value: float
    ratio: float | None
    passed: bool
    treatment: str
    reason: str


class SdaBenchmarkReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[G9_REPORT_SCHEMA] = G9_REPORT_SCHEMA
    protocol_id: str
    baseline_bundle_id: str
    candidate_bundle_id: str
    results: list[SdaMetricResult]
    mandatory_security_passed: bool
    mandatory_utility_passed: bool
    ten_x_security_claim_eligible: bool
    preserved_zero_invariants: list[str]
    ten_x_improved_metrics: list[str]
    claims_boundary: str = (
        "Eligibility is limited to the frozen protocol, workload, environment and "
        "measurement evidence supplied to this evaluator. It is not a universal "
        "10x-security claim, operational accreditation, penetration-test result, "
        "government acceptance, or independent validation."
    )


def _measurement_map(
    bundle: SdaBenchmarkMeasurementBundle,
) -> dict[str, SdaMetricMeasurement]:
    return {item.metric_id: item for item in bundle.measurements}


def evaluate_g9(
    protocol: SdaBenchmarkProtocol,
    baseline: SdaBenchmarkMeasurementBundle,
    candidate: SdaBenchmarkMeasurementBundle,
) -> SdaBenchmarkReport:
    if baseline.role != "BASELINE" or candidate.role != "CANDIDATE":
        raise SdaBenchmarkError("benchmark roles must be BASELINE and CANDIDATE")
    if baseline.environment_id != candidate.environment_id:
        raise SdaBenchmarkError("baseline and candidate environment IDs differ")
    if baseline.environment_id != protocol.required_environment_id:
        raise SdaBenchmarkError("measurement environment does not match protocol")
    if baseline.workload_sha256 != candidate.workload_sha256:
        raise SdaBenchmarkError("baseline and candidate workloads differ")
    if baseline.workload_sha256 != protocol.g8_corpus_sha256:
        raise SdaBenchmarkError("measurement workload does not match frozen G8 corpus")

    baseline_map = _measurement_map(baseline)
    candidate_map = _measurement_map(candidate)
    expected = {item.metric_id for item in protocol.metrics}
    if set(baseline_map) != expected or set(candidate_map) != expected:
        raise SdaBenchmarkError("baseline/candidate must measure every protocol metric")

    results: list[SdaMetricResult] = []
    zero_invariants: list[str] = []
    ten_x_metrics: list[str] = []

    for metric in protocol.metrics:
        before = baseline_map[metric.metric_id]
        after = candidate_map[metric.metric_id]

        if before.unit != metric.unit or after.unit != metric.unit:
            raise SdaBenchmarkError(f"unit mismatch for {metric.metric_id}")
        if before.sample_count < metric.min_samples:
            raise SdaBenchmarkError(f"baseline sample count too small for {metric.metric_id}")
        if after.sample_count < metric.min_samples:
            raise SdaBenchmarkError(f"candidate sample count too small for {metric.metric_id}")

        ratio: float | None = None
        treatment = ""
        reason = ""
        passed = False

        if metric.metric_class == MetricClass.SECURITY:
            if metric.security_treatment == SecurityTreatment.ZERO_INVARIANT:
                treatment = "ZERO_INVARIANT"
                passed = after.value == 0.0
                reason = (
                    "candidate preserved zero residual"
                    if passed
                    else "candidate violated zero-residual invariant"
                )
                if passed:
                    zero_invariants.append(metric.metric_id)
            elif metric.security_treatment == SecurityTreatment.RATIO_OR_ZERO_INVARIANT:
                if before.value == 0.0:
                    treatment = "BASELINE_ZERO_INVARIANT"
                    passed = after.value == 0.0
                    reason = (
                        "baseline was already zero; candidate preserved zero"
                        if passed
                        else "baseline was zero but candidate regressed above zero"
                    )
                    if passed:
                        zero_invariants.append(metric.metric_id)
                else:
                    ratio = after.value / before.value
                    treatment = "TEN_X_RATIO"
                    threshold = metric.max_candidate_to_baseline_ratio
                    assert threshold is not None
                    # Measurements are represented as finite binary floats in v1.
                    # A machine-epsilon-scale tolerance prevents 0.03/0.30 from
                    # failing solely because it is represented as 0.10000000000000002.
                    # The tolerance is far too small to mask a substantive miss.
                    tolerance = 1e-12 * max(1.0, threshold)
                    passed = ratio <= threshold + tolerance
                    reason = (
                        f"candidate/baseline={ratio:.6g} <= {threshold:.6g}"
                        if passed
                        else f"candidate/baseline={ratio:.6g} > {threshold:.6g}"
                    )
                    if passed:
                        ten_x_metrics.append(metric.metric_id)
            else:
                raise SdaBenchmarkError("invalid security treatment")
        else:
            budget = metric.max_relative_regression
            assert budget is not None
            treatment = "UTILITY_NON_REGRESSION"
            if metric.direction == MetricDirection.LOWER_IS_BETTER:
                allowed = before.value * (1.0 + budget)
                if before.value == 0.0:
                    allowed = budget
                passed = after.value <= allowed
                reason = f"candidate={after.value:.6g}, maximum={allowed:.6g}"
            else:
                allowed = before.value * (1.0 - budget)
                passed = after.value >= allowed
                reason = f"candidate={after.value:.6g}, minimum={allowed:.6g}"

        results.append(
            SdaMetricResult(
                metric_id=metric.metric_id,
                metric_class=metric.metric_class,
                mandatory=metric.mandatory,
                baseline_value=before.value,
                candidate_value=after.value,
                ratio=ratio,
                passed=passed,
                treatment=treatment,
                reason=reason,
            )
        )

    mandatory_security = [
        item
        for item in results
        if item.metric_class == MetricClass.SECURITY and item.mandatory
    ]
    mandatory_utility = [
        item
        for item in results
        if item.metric_class == MetricClass.UTILITY and item.mandatory
    ]
    security_pass = bool(mandatory_security) and all(item.passed for item in mandatory_security)
    utility_pass = all(item.passed for item in mandatory_utility)

    # Eligibility requires every mandatory security dimension to pass, every
    # mandatory utility non-regression gate to pass, and at least one genuine
    # non-zero-baseline metric to demonstrate a measured >=10x reduction.
    eligible = security_pass and utility_pass and bool(ten_x_metrics)

    return SdaBenchmarkReport(
        protocol_id=protocol.protocol_id,
        baseline_bundle_id=baseline.bundle_id,
        candidate_bundle_id=candidate.bundle_id,
        results=results,
        mandatory_security_passed=security_pass,
        mandatory_utility_passed=utility_pass,
        ten_x_security_claim_eligible=eligible,
        preserved_zero_invariants=sorted(zero_invariants),
        ten_x_improved_metrics=sorted(ten_x_metrics),
    )
