from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Sequence

from model import FlexRequest
from trace import TracePoint


class MeasurementBoundary(str, Enum):
    DEVICE = "device"
    NODE = "node"
    CLUSTER = "cluster"
    PDU = "pdu"
    FACILITY = "facility"
    GRID_BOUNDARY = "grid_boundary"


@dataclass(frozen=True)
class PartnerEvidenceContext:
    """Declared custody/evidence state for a partner-origin event bundle.

    This structure records what the partner evidence actually establishes. It
    never promotes a lower-level measurement boundary into a facility/grid
    claim and never infers missing request, authorization, clock, baseline, or
    configuration evidence.
    """

    source_organization: str
    project_or_dataset_id: str
    measurement_boundary: MeasurementBoundary
    request_id: str | None
    authorization_record_id: str | None
    clock_source: str | None
    baseline_method: str | None
    configuration_id: str | None
    meter_id: str | None
    authorized: bool = True
    request_provenance_valid: bool = True
    authorization_evidence_valid: bool = True
    clocks_synchronized: bool = True
    baseline_valid: bool = True
    configuration_custody_valid: bool = True
    transformation_history: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    @property
    def claim_scope(self) -> str:
        if self.measurement_boundary is MeasurementBoundary.GRID_BOUNDARY:
            return "grid_boundary"
        if self.measurement_boundary is MeasurementBoundary.FACILITY:
            return "facility_only"
        return f"{self.measurement_boundary.value}_only"


def _present(value: str | None) -> bool:
    return bool(value and value.strip())


def build_partner_replay_payload(
    request: FlexRequest,
    baseline_mw: float,
    points: Sequence[TracePoint],
    context: PartnerEvidenceContext,
    *,
    max_gap_s: float = 300.0,
    energy_mismatch_tolerance_mwh: float = 0.25,
) -> dict:
    """Build a replay payload from partner-origin evidence without inference.

    Required identifiers are folded into evidence-validity flags. Declared
    configuration and meter identities must also agree with every trace point;
    merely supplying a label in the manifest cannot establish custody.
    """

    source_identity_valid = _present(context.source_organization) and _present(
        context.project_or_dataset_id
    )
    request_provenance_valid = (
        context.request_provenance_valid and _present(context.request_id)
    )
    authorization_evidence_valid = (
        context.authorization_evidence_valid
        and _present(context.authorization_record_id)
    )
    clocks_synchronized = context.clocks_synchronized and _present(context.clock_source)
    baseline_valid = context.baseline_valid and _present(context.baseline_method)

    configuration_identity_matches = _present(context.configuration_id) and all(
        point.configuration_id == context.configuration_id for point in points
    )
    configuration_custody_valid = (
        context.configuration_custody_valid and configuration_identity_matches
    )

    meter_identity_matches = _present(context.meter_id) and all(
        point.meter_id == context.meter_id for point in points
    )
    normalized_points = [
        replace(
            point,
            meter_provenance_valid=(
                point.meter_provenance_valid and meter_identity_matches
            ),
        )
        for point in points
    ]

    payload = {
        "request": asdict(request),
        "baseline_mw": baseline_mw,
        "authorized": context.authorized,
        "source_identity_valid": source_identity_valid,
        "request_provenance_valid": request_provenance_valid,
        "authorization_evidence_valid": authorization_evidence_valid,
        "clocks_synchronized": clocks_synchronized,
        "baseline_valid": baseline_valid,
        "configuration_custody_valid": configuration_custody_valid,
        "max_gap_s": max_gap_s,
        "energy_mismatch_tolerance_mwh": energy_mismatch_tolerance_mwh,
        "points": [asdict(point) for point in normalized_points],
        "provenance": {
            "source_organization": context.source_organization,
            "project_or_dataset_id": context.project_or_dataset_id,
            "measurement_boundary": context.measurement_boundary.value,
            "claim_scope": context.claim_scope,
            "request_id": context.request_id,
            "authorization_record_id": context.authorization_record_id,
            "clock_source": context.clock_source,
            "baseline_method": context.baseline_method,
            "configuration_id": context.configuration_id,
            "meter_id": context.meter_id,
            "configuration_identity_matches_trace": configuration_identity_matches,
            "meter_identity_matches_trace": meter_identity_matches,
            "transformation_history": list(context.transformation_history),
            "limitations": list(context.limitations),
            "evidence_policy": "partner_origin_fail_closed",
        },
    }
    return payload
