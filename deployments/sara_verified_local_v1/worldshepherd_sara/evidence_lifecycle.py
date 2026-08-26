from __future__ import annotations

from .qualification import (
    QualificationEvidenceRecord,
    ReviewRecord,
    ReviewStatus,
    SupersessionRecord,
    SupersessionState,
)


def supersede_evidence(
    record: QualificationEvidenceRecord,
    *,
    superseded_by: str,
    reviewer: str,
    reviewed_utc: str,
) -> QualificationEvidenceRecord:
    if record.supersession.state != SupersessionState.CURRENT:
        raise ValueError("only CURRENT evidence may be superseded")
    return record.model_copy(
        update={
            "review": ReviewRecord(
                status=ReviewStatus.ACCEPTED,
                reviewer=reviewer,
                reviewed_utc=reviewed_utc,
            ),
            "supersession": SupersessionRecord(
                state=SupersessionState.SUPERSEDED,
                superseded_by=superseded_by,
            ),
        }
    )


def revoke_evidence(
    record: QualificationEvidenceRecord,
    *,
    reviewer: str,
    reviewed_utc: str,
    reason: str,
) -> QualificationEvidenceRecord:
    if record.supersession.state == SupersessionState.REVOKED:
        raise ValueError("evidence is already revoked")
    negative = list(record.negative_evidence)
    negative.append({"revocation_reason": reason, "reviewer": reviewer})
    return record.model_copy(
        update={
            "negative_evidence": negative,
            "review": ReviewRecord(
                status=ReviewStatus.REJECTED,
                reviewer=reviewer,
                reviewed_utc=reviewed_utc,
            ),
            "supersession": SupersessionRecord(
                state=SupersessionState.REVOKED,
                superseded_by=None,
            ),
        }
    )
