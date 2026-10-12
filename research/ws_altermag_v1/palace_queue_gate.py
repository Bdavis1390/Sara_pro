from __future__ import annotations

import csv
from pathlib import Path


REQUIRED_FIELDS = {"anchor_id", "exit_code", "status"}


def inspect_palace_queue(
    results_path: Path,
    expected_anchor_ids: list[int] | range,
    *,
    require_all_exit0: bool = True,
) -> dict:
    """Read-only clearance check for a queued Palace solver campaign.

    This is a scheduling/resource gate, NOT a numerical-accuracy verdict.
    A completed EXIT0 Palace job may still have GMRES convergence warnings.
    """
    expected = [int(i) for i in expected_anchor_ids]
    if not expected or len(set(expected)) != len(expected):
        raise ValueError("expected anchor IDs must be nonempty and unique")

    base = {
        "results_path": str(results_path),
        "expected_count": len(expected),
        "require_all_exit0": require_all_exit0,
        "receipt_present": results_path.is_file(),
    }
    if not results_path.is_file():
        return {
            **base,
            "completed_ids": [],
            "missing_ids": sorted(expected),
            "failed_ids": [],
            "duplicate_ids": [],
            "malformed_rows": 0,
            "queue_clear": False,
            "decision": "BLOCK_PALACE_QUEUE_INCOMPLETE",
        }

    records: dict[int, tuple[str, str]] = {}
    duplicates: set[int] = set()
    malformed = 0
    with results_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not REQUIRED_FIELDS.issubset(reader.fieldnames or []):
            return {
                **base,
                "completed_ids": [],
                "missing_ids": sorted(expected),
                "failed_ids": [],
                "duplicate_ids": [],
                "malformed_rows": 1,
                "queue_clear": False,
                "decision": "BLOCK_PALACE_QUEUE_MALFORMED_RECEIPT",
            }
        for row in reader:
            try:
                anchor = int(row["anchor_id"])
                code = int(row["exit_code"])
                status = str(row["status"]).strip()
            except (TypeError, ValueError, KeyError):
                malformed += 1
                continue
            if anchor in records:
                duplicates.add(anchor)
            records[anchor] = (str(code), status)

    completed = sorted(set(expected) & set(records))
    missing = sorted(set(expected) - set(records))
    failed = sorted(
        i for i in completed
        if require_all_exit0 and records[i] != ("0", "EXIT0")
    )
    clear = not missing and not failed and not duplicates and not malformed
    return {
        **base,
        "completed_ids": completed,
        "missing_ids": missing,
        "failed_ids": failed,
        "duplicate_ids": sorted(duplicates),
        "malformed_rows": malformed,
        "queue_clear": clear,
        "decision": "PALACE_QUEUE_CLEAR" if clear else "BLOCK_PALACE_QUEUE_INCOMPLETE",
        "claim_boundary": (
            "Queue completion is an execution-scheduling fact, not proof "
            "of GMRES convergence, electromagnetic correctness or device performance."
        ),
    }
