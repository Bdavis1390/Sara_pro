"""Aggregate already-verified WS-CAE transparency statement payloads.

This module does not verify signatures or receipts. It operates on statement
payloads after cryptographic verification and preserves disagreements rather
than deciding which issuer is correct.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Iterable

from .scitt_statement import sha256_hex

TIMELINE_SPEC = "WS-CAE-TRANSPARENCY-TIMELINE-1"


def _parse_time(value: str) -> datetime:
    if not value:
        raise ValueError("observed_at must be non-empty")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid observed_at: {value}") from exc


@dataclass(frozen=True)
class Conflict:
    kind: str
    subject_id: str
    observed_at: str
    issuers: tuple[str, ...]
    claim_digests: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_timeline(statements: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for statement in statements:
        subject = statement.get("subject")
        claims = statement.get("claims")
        issuer = str(statement.get("issuer", "")).strip()
        observed_at = str(statement.get("observed_at", "")).strip()
        if not isinstance(subject, dict) or not str(subject.get("id", "")).strip():
            raise ValueError("every statement requires subject.id")
        if not isinstance(claims, dict):
            raise ValueError("every statement requires claims object")
        if not issuer:
            raise ValueError("every statement requires issuer")
        parsed_time = _parse_time(observed_at)
        rows.append(
            {
                "subject_id": str(subject["id"]),
                "subject_name": str(subject.get("name", "")),
                "issuer": issuer,
                "observed_at": observed_at,
                "_time": parsed_time,
                "claim_digest": sha256_hex(claims),
                "source_patch_sha256": str(subject.get("source_patch_sha256", "")),
                "statement_digest": sha256_hex(statement),
                "claims": claims,
            }
        )

    rows.sort(key=lambda row: (row["subject_id"], row["_time"], row["issuer"], row["statement_digest"]))

    conflicts: list[Conflict] = []
    by_subject_time: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_subject_time_issuer: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_subject_time[(row["subject_id"], row["observed_at"])].append(row)
        by_subject_time_issuer[(row["subject_id"], row["observed_at"], row["issuer"])].append(row)

    for (subject_id, observed_at, issuer), group in sorted(by_subject_time_issuer.items()):
        digests = sorted({row["claim_digest"] for row in group})
        if len(digests) > 1:
            conflicts.append(
                Conflict(
                    "ISSUER_EQUIVOCATION",
                    subject_id,
                    observed_at,
                    (issuer,),
                    tuple(digests),
                )
            )

    for (subject_id, observed_at), group in sorted(by_subject_time.items()):
        issuers = sorted({row["issuer"] for row in group})
        digests = sorted({row["claim_digest"] for row in group})
        if len(issuers) > 1 and len(digests) > 1:
            conflicts.append(
                Conflict(
                    "CROSS_ISSUER_DISAGREEMENT",
                    subject_id,
                    observed_at,
                    tuple(issuers),
                    tuple(digests),
                )
            )

    public_rows = []
    for row in rows:
        public_rows.append({key: value for key, value in row.items() if key != "_time"})

    latest_by_subject: dict[str, str] = {}
    for row in rows:
        latest_by_subject[row["subject_id"]] = row["observed_at"]

    return {
        "spec": TIMELINE_SPEC,
        "statement_count": len(public_rows),
        "subject_count": len({row["subject_id"] for row in rows}),
        "latest_observation_by_subject": latest_by_subject,
        "statements": public_rows,
        "conflicts": [conflict.to_dict() for conflict in conflicts],
    }
