from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


EXTERNAL_GAP_LEDGER_SCHEMA = "ws-external-gap-ledger-1"


class GapClass(str, Enum):
    REAL_INTERNAL_GAP = "REAL_INTERNAL_GAP"
    PROOF_SURFACE_GAP = "PROOF_SURFACE_GAP"
    POSITIONING_GAP = "POSITIONING_GAP"
    PARTNER_GAP = "PARTNER_GAP"
    EXTERNAL_VALIDATION_GAP = "EXTERNAL_VALIDATION_GAP"
    LEGAL_ENTITY_COMPLIANCE_GAP = "LEGAL_ENTITY_COMPLIANCE_GAP"
    VENUE_SCOPE_MISMATCH = "VENUE_SCOPE_MISMATCH"
    NOT_A_WORLDSHEPHERD_GAP = "NOT_A_WORLDSHEPHERD_GAP"


class GapStatus(str, Enum):
    INTAKE = "INTAKE"
    ROUTED = "ROUTED"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class SourceVisibility(str, Enum):
    PUBLIC = "PUBLIC"
    CONTROLLED = "CONTROLLED"
    PRIVATE = "PRIVATE"


_FAIL_CLOSED_CLASSES = {
    GapClass.PARTNER_GAP,
    GapClass.EXTERNAL_VALIDATION_GAP,
    GapClass.LEGAL_ENTITY_COMPLIANCE_GAP,
}


class ExternalGapRecord(BaseModel):
    gap_id: str = Field(min_length=4, max_length=96)
    source_org: str = Field(min_length=1, max_length=200)
    source_date: date
    source_channel: str = Field(min_length=1, max_length=80)
    source_ref: str = Field(min_length=1, max_length=300)
    source_visibility: SourceVisibility = SourceVisibility.CONTROLLED
    feedback_summary: str = Field(min_length=1, max_length=3000)
    classification: GapClass
    confidence: float = Field(ge=0.0, le=1.0)
    systemic_key: str = Field(min_length=1, max_length=160)
    authoritative_evidence_checked: list[str] = Field(default_factory=list)
    route_issue_refs: list[str] = Field(default_factory=list)
    owner: str = Field(min_length=1, max_length=160)
    action: str = Field(min_length=1, max_length=3000)
    closure_evidence: list[str] = Field(default_factory=list)
    claims_effect: str = Field(min_length=1, max_length=3000)
    status: GapStatus = GapStatus.INTAKE

    @model_validator(mode="after")
    def validate_closure(self) -> "ExternalGapRecord":
        if self.status == GapStatus.CLOSED and not self.closure_evidence:
            raise ValueError("CLOSED gap records require closure_evidence")
        if self.status in {GapStatus.ROUTED, GapStatus.IN_PROGRESS, GapStatus.CLOSED}:
            if not self.route_issue_refs:
                raise ValueError(
                    f"{self.status.value} gap records require at least one route_issue_ref"
                )
        return self

    @property
    def claim_promotion_blocked(self) -> bool:
        return (
            self.classification in _FAIL_CLOSED_CLASSES
            and self.status != GapStatus.CLOSED
        )


class ExternalGapLedger(BaseModel):
    schema_version: str = EXTERNAL_GAP_LEDGER_SCHEMA
    records: list[ExternalGapRecord]

    @model_validator(mode="after")
    def validate_unique_gap_ids(self) -> "ExternalGapLedger":
        ids = [item.gap_id for item in self.records]
        duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate gap_id values: {duplicates}")
        return self

    def systemic_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.systemic_key for item in self.records).items()))

    def class_counts(self) -> dict[str, int]:
        return dict(
            sorted(Counter(item.classification.value for item in self.records).items())
        )

    def open_fail_closed_gap_ids(self) -> list[str]:
        return sorted(
            item.gap_id for item in self.records if item.claim_promotion_blocked
        )

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def digest(self) -> str:
        payload = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def ledger_summary(ledger: ExternalGapLedger) -> dict[str, Any]:
    return {
        "schema_version": ledger.schema_version,
        "record_count": len(ledger.records),
        "ledger_sha256": ledger.digest(),
        "class_counts": ledger.class_counts(),
        "systemic_counts": ledger.systemic_counts(),
        "open_fail_closed_gap_ids": ledger.open_fail_closed_gap_ids(),
    }


def load_ledger(path: str | Path) -> ExternalGapLedger:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return ExternalGapLedger.model_validate(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and summarize a Worldshepherd external-feedback gap ledger."
        )
    )
    parser.add_argument("ledger", nargs="?", help="Path to ledger JSON")
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Print the JSON Schema for the ledger format and exit.",
    )
    args = parser.parse_args(argv)

    if args.schema:
        print(
            json.dumps(
                ExternalGapLedger.model_json_schema(), indent=2, sort_keys=True
            )
        )
        return 0

    if not args.ledger:
        parser.error("ledger path is required unless --schema is used")

    ledger = load_ledger(args.ledger)
    print(json.dumps(ledger_summary(ledger), indent=2, sort_keys=True))
    return 2 if ledger.open_fail_closed_gap_ids() else 0


if __name__ == "__main__":
    raise SystemExit(main())
