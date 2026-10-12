"""Evidence-custodied cryptographic inventory model for PQC migration planning.

This is an internal Worldshepherd engineering artifact inspired by public
Federal PQC migration guidance. It does not establish Federal compliance,
asset authorization, or certification.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date


@dataclass(frozen=True)
class CryptoAsset:
    asset_id: str
    system_name: str
    owner: str
    algorithm_family: str
    cryptographic_role: str
    high_value_asset: bool = False
    high_impact_system: bool = False
    highly_sensitive_data: bool = False
    mission_sensitive_after_2030: bool = False
    pqc_ready: bool = False
    crypto_agile: bool = False
    supplier_dependency: str = ""
    evidence_source: str = ""
    last_verified: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def validate_asset(asset: CryptoAsset) -> tuple[str, ...]:
    missing: list[str] = []
    for field_name, value in (
        ("asset_id", asset.asset_id),
        ("system_name", asset.system_name),
        ("owner", asset.owner),
        ("algorithm_family", asset.algorithm_family),
        ("cryptographic_role", asset.cryptographic_role),
        ("evidence_source", asset.evidence_source),
        ("last_verified", asset.last_verified),
    ):
        if not value or not value.strip():
            missing.append(field_name)
    return tuple(missing)


def priority_band(asset: CryptoAsset) -> str:
    """Conservative migration-priority band for internal planning.

    This is not an official Federal score. It only mirrors public priority
    concepts: HVA/high-impact, highly sensitive data, long-lived sensitivity,
    PQC readiness, and cryptographic agility.
    """
    if validate_asset(asset):
        return "INCOMPLETE_EVIDENCE"

    critical = asset.high_value_asset or asset.high_impact_system
    sensitive = asset.highly_sensitive_data or asset.mission_sensitive_after_2030

    if critical and not asset.pqc_ready:
        return "P0_MIGRATION_PRIORITY"
    if sensitive and not asset.pqc_ready:
        return "P1_MIGRATION_PRIORITY"
    if not asset.pqc_ready or not asset.crypto_agile:
        return "P2_MODERNIZATION_PRIORITY"
    return "P3_MONITOR"


def inventory_summary(assets: tuple[CryptoAsset, ...]) -> dict[str, object]:
    bands: dict[str, int] = {}
    missing_records = 0
    for asset in assets:
        band = priority_band(asset)
        bands[band] = bands.get(band, 0) + 1
        if band == "INCOMPLETE_EVIDENCE":
            missing_records += 1

    return {
        "asset_count": len(assets),
        "priority_bands": bands,
        "incomplete_evidence_records": missing_records,
        "claim_boundary": "INTERNAL_CBOM_MODEL_NOT_FEDERAL_COMPLIANCE",
    }
