from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode


class ExpectedEnvelope(BaseModel):
    metric: str = Field(min_length=1)
    minimum: float
    maximum: float
    units: str | None = None


class TelemetrySample(BaseModel):
    sample_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: float
    t_seconds: float = Field(ge=0)
    source_ref: str = Field(min_length=1)


@dataclass(frozen=True)
class HealthFinding:
    sample_id: str
    asset_id: str
    metric: str
    status: str
    deviation: float
    expected_minimum: float
    expected_maximum: float


def evaluate_sample(sample: TelemetrySample, envelope: ExpectedEnvelope) -> HealthFinding:
    if sample.metric != envelope.metric:
        raise ValueError("sample metric and envelope metric must match")
    if envelope.minimum > envelope.maximum:
        raise ValueError("envelope minimum cannot exceed maximum")
    if sample.value < envelope.minimum:
        status = "LOW"
        deviation = envelope.minimum - sample.value
    elif sample.value > envelope.maximum:
        status = "HIGH"
        deviation = sample.value - envelope.maximum
    else:
        status = "NOMINAL"
        deviation = 0.0
    return HealthFinding(
        sample_id=sample.sample_id,
        asset_id=sample.asset_id,
        metric=sample.metric,
        status=status,
        deviation=deviation,
        expected_minimum=envelope.minimum,
        expected_maximum=envelope.maximum,
    )


def evaluate_series(
    samples: list[TelemetrySample], envelopes: dict[str, ExpectedEnvelope]
) -> tuple[HealthFinding, ...]:
    findings: list[HealthFinding] = []
    for sample in sorted(samples, key=lambda item: (item.t_seconds, item.sample_id)):
        if sample.metric not in envelopes:
            raise KeyError(f"no expected envelope for metric {sample.metric}")
        findings.append(evaluate_sample(sample, envelopes[sample.metric]))
    return tuple(findings)


def health_graph(
    *, graph_id: str, samples: list[TelemetrySample], findings: tuple[HealthFinding, ...]
) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []
    for sample in samples:
        nodes.append(
            EvidenceGraphNode(
                node_id=f"sample:{sample.sample_id}",
                node_type="telemetry_sample",
                label=f"{sample.asset_id}:{sample.metric}",
                source_ref=sample.source_ref,
                attributes=sample.model_dump(mode="json"),
            )
        )
    for index, finding in enumerate(findings, start=1):
        finding_id = f"health:{index:04d}"
        nodes.append(
            EvidenceGraphNode(
                node_id=finding_id,
                node_type="cbm_health_finding",
                label=finding.status,
                attributes={
                    "asset_id": finding.asset_id,
                    "metric": finding.metric,
                    "deviation": finding.deviation,
                    "expected_minimum": finding.expected_minimum,
                    "expected_maximum": finding.expected_maximum,
                },
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=f"edge:{finding.sample_id}:{index}",
                source_node_id=f"sample:{finding.sample_id}",
                target_node_id=finding_id,
                relation="supports_health_finding",
                source_ref=f"sample:{finding.sample_id}",
                confidence=1.0,
            )
        )
    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)
