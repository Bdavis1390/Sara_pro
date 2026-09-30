from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from math import isfinite

from model import FlexRequest
from trace import TracePoint


@dataclass(frozen=True)
class ExternalTraceManifest:
    """Immutable identity and declared transformation context for an external trace."""

    source_name: str
    source_repository: str
    source_path: str
    source_ref: str
    source_git_blob_sha1: str
    upstream_dataset_doi: str
    system_base_mw: float
    data_center_base_mw: float
    claim_status: str


PSCAD_NLR_SURROGATE = ExternalTraceManifest(
    source_name="PSCAD/Hypersim Llama2 training-load surrogate",
    source_repository="bram-exe/PSCAD-Hypersim-Data-Center-Modeling",
    source_path="Training Load Simulation/pscad_load_short.csv",
    source_ref="main",
    source_git_blob_sha1="693cb03b53af4d6fdeee72c88269c0e5dd0a48e9",
    upstream_dataset_doi="10.7799/3025227",
    system_base_mw=5000.0,
    data_center_base_mw=250.0,
    claim_status="EXTERNAL PROCESSED SURROGATE / NOT PARTNER VALIDATION",
)


def git_blob_sha1(text: str) -> str:
    """Return the Git object ID for UTF-8 text using Git's blob framing."""

    data = text.encode("utf-8")
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_source_blob(text: str, manifest: ExternalTraceManifest) -> None:
    actual = git_blob_sha1(text)
    if actual != manifest.source_git_blob_sha1:
        raise ValueError(
            "external_source_blob_mismatch: "
            f"expected={manifest.source_git_blob_sha1} actual={actual}"
        )


def parse_pscad_deviation_text(
    text: str,
    *,
    manifest: ExternalTraceManifest = PSCAD_NLR_SURROGATE,
) -> tuple[TracePoint, ...]:
    """Map a PSCAD `time dP_pu` trace into FLEX-001 load observations.

    The upstream trace is a processed/scaled load deviation, not an
    authoritative utility meter. Consequently every imported point is marked
    with invalid grid-meter provenance. This prevents the adapter from turning
    an external modeled/load-derived trace into a false field verification.
    """

    points: list[TracePoint] = []
    configuration_id = f"external:{manifest.source_git_blob_sha1[:12]}:unknown-config"
    meter_id = "external-derived-load:not-authoritative-grid-meter"

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("!") or line.startswith("#"):
            continue
        fields = line.replace(",", " ").split()
        if len(fields) < 2:
            raise ValueError(f"invalid_external_row:{line_number}")
        try:
            timestamp_s = float(fields[0])
            deviation_pu = float(fields[1])
        except ValueError as exc:
            raise ValueError(f"invalid_external_numeric:{line_number}") from exc
        if not isfinite(timestamp_s) or not isfinite(deviation_pu):
            raise ValueError(f"nonfinite_external_numeric:{line_number}")
        if timestamp_s < 0:
            raise ValueError(f"negative_external_timestamp:{line_number}")

        grid_import_mw = (
            manifest.data_center_base_mw
            + deviation_pu * manifest.system_base_mw
        )
        if not isfinite(grid_import_mw) or grid_import_mw < 0:
            raise ValueError(f"invalid_external_load_mapping:{line_number}")

        points.append(
            TracePoint(
                timestamp_s=timestamp_s,
                grid_import_mw=grid_import_mw,
                telemetry_fresh=True,
                meter_provenance_valid=False,
                configuration_id=configuration_id,
                meter_id=meter_id,
            )
        )

    if len(points) < 2:
        raise ValueError("insufficient_external_trace_samples")
    return tuple(points)


def build_external_surrogate_payload(
    text: str,
    request: FlexRequest,
    *,
    manifest: ExternalTraceManifest = PSCAD_NLR_SURROGATE,
    require_blob_match: bool = True,
) -> dict:
    """Build a fail-closed replay payload for an external processed trace.

    The adapter preserves source identity and transformation context while
    explicitly marking evidence that the external trace does *not* establish:
    request provenance, authorization provenance, field baseline validity,
    synchronized clock provenance, configuration custody, and authoritative
    grid-meter provenance.

    Those flags must remain false for this surrogate. A partner evidence bundle
    should be built separately from authoritative source records rather than by
    promoting this payload.
    """

    if require_blob_match:
        validate_source_blob(text, manifest)
    points = parse_pscad_deviation_text(text, manifest=manifest)
    return {
        "request": asdict(request),
        "baseline_mw": manifest.data_center_base_mw,
        "authorized": False,
        "authorization_evidence_valid": False,
        "request_provenance_valid": False,
        "baseline_valid": False,
        "clocks_synchronized": False,
        "configuration_custody_valid": False,
        "max_gap_s": 1.0,
        "points": [asdict(point) for point in points],
        "provenance": {
            "source": asdict(manifest),
            "source_sha256": sha256_text(text),
            "adapter": "ws_dcar_flex_001.external_surrogate",
            "transformation": (
                "grid_import_mw = data_center_base_mw + "
                "dP_pu * system_base_mw"
            ),
            "evidence_policy": "fail_closed_external_surrogate",
        },
    }
