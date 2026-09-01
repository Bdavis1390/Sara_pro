from __future__ import annotations

import json

import pytest

from worldshepherd_sara.intake_minimum_cli import (
    INTAKE_MINIMUM_SCHEMA,
    build_intake_minimum_ledger,
    main,
    normalize_intake_record,
)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _base_intake(**overrides):
    record = {
        "intake_id": "WS-INTAKE-2026-09-01-001",
        "intake_type": "USER_DIRECTIVE",
        "source_system": "chatgpt_conversation",
        "source_locator": "conversation:continue-to-this-extent-with-every-new-intake",
        "source_retrieved_utc": "2026-09-01T18:25:00Z",
        "source_sha256": "sha256:" + "1" * 64,
        "evidence_status": "RAW_INTAKE_UNSIGNED",
        "maturity_label": "RAW_INTAKE",
        "human_review_status": "PENDING_HUMAN_REVIEW",
        "routing_status": "ROUTED_TO_BACKLOG",
        "downstream_route": "Convert directive into intake minimum standard ledger and CI enforcement.",
        "claims_boundary": "This intake does not establish validation, compliance, remediation, award probability, partner interest, or operational authority.",
        "owner": "CRE1AWS",
        "priority": "HIGH",
    }
    record.update(overrides)
    return record


def test_normalize_intake_record_requires_every_minimum_control() -> None:
    record = normalize_intake_record(_base_intake())

    assert record["intake_id"] == "WS-INTAKE-2026-09-01-001"
    assert record["source_sha256"] == "sha256:" + "1" * 64
    assert record["minimum_controls"] == {
        "source_custody": "PASS",
        "source_hash": "PASS",
        "claims_boundary": "PASS",
        "human_review_status": "PASS",
        "routing_status": "PASS",
        "downstream_route_or_evidence": "PASS",
        "false_claim_guard": "PASS",
    }
    assert record["record_digest"].startswith("sha256:")


def test_build_intake_minimum_ledger_summarizes_review_and_routing_counts(tmp_path) -> None:
    intake_file = tmp_path / "intakes.json"
    _write_json(
        intake_file,
        {
            "intakes": [
                _base_intake(),
                _base_intake(
                    intake_id="WS-INTAKE-2026-09-01-002",
                    source_sha256="sha256:" + "2" * 64,
                    human_review_status="REVIEWED_ACTION_REQUIRED",
                    routing_status="ROUTED_TO_TRIAGE",
                    review_rationale="Human owner identified this as actionable but not yet remediated.",
                    downstream_route="Create a remediation-action evidence record before any claim upgrade.",
                ),
                _base_intake(
                    intake_id="WS-INTAKE-2026-09-01-003",
                    source_sha256="sha256:" + "3" * 64,
                    human_review_status="HUMAN_REVIEW_NOT_REQUIRED",
                    routing_status="NOT_MATERIAL",
                    maturity_label="NOT_CURRENTLY_CLAIMED",
                    downstream_route="No follow-on route because the source was screened as not material.",
                    claims_boundary="No validation, compliance, remediation, partner-interest, or operational-authority claim is made.",
                ),
            ]
        },
    )

    ledger = build_intake_minimum_ledger(
        intake_file=intake_file,
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        operator="github-actions",
        executed_utc="2026-09-01T18:30:00Z",
    )

    assert ledger["schema"] == INTAKE_MINIMUM_SCHEMA
    assert ledger["summary"]["intake_count"] == 3
    assert ledger["summary"]["pending_human_review_count"] == 1
    assert ledger["summary"]["reviewed_action_required_count"] == 1
    assert ledger["summary"]["not_material_count"] == 1
    assert ledger["ledger_digest"].startswith("sha256:")
    assert "does not establish" in ledger["claims_boundary"]
    assert "award probability" in ledger["claims_boundary"]


def test_intake_minimum_cli_writes_ledger_and_summary(tmp_path) -> None:
    intake_file = tmp_path / "intakes.json"
    out_dir = tmp_path / "intake_minimum_ci"
    _write_json(intake_file, {"intakes": [_base_intake()]})

    exit_code = main(
        [
            "--intake-file",
            str(intake_file),
            "--out",
            str(out_dir),
            "--repository",
            "Bdavis1390/Sara_pro",
            "--commit-sha",
            "abc123",
            "--operator",
            "github-actions",
            "--executed-utc",
            "2026-09-01T18:31:00Z",
        ]
    )

    assert exit_code == 0
    ledger = json.loads((out_dir / "intake-minimum-ledger.json").read_text(encoding="utf-8"))
    summary = json.loads((out_dir / "intake-minimum-summary.json").read_text(encoding="utf-8"))
    assert ledger["schema"] == INTAKE_MINIMUM_SCHEMA
    assert summary["schema"] == INTAKE_MINIMUM_SCHEMA
    assert summary["evidence_status"] == "INTERNAL_INTAKE_STANDARD_UNSIGNED"
    assert summary["intake_count"] == 1
    assert summary["pending_human_review_count"] == 1
    assert summary["intake_minimum_ledger_sha256"].startswith("sha256:")
    assert summary["intake_minimum_ledger_file_sha256"].startswith("sha256:")


def test_intake_minimum_rejects_missing_required_field() -> None:
    record = _base_intake()
    record.pop("source_locator")

    with pytest.raises(ValueError, match="missing required fields: source_locator"):
        normalize_intake_record(record)


def test_intake_minimum_rejects_bad_source_digest() -> None:
    with pytest.raises(ValueError, match="source_sha256 must be a SHA-256 digest"):
        normalize_intake_record(_base_intake(source_sha256="not-a-digest"))


def test_intake_minimum_rejects_claim_boundary_without_non_claim_language() -> None:
    with pytest.raises(ValueError, match="claims_boundary must contain explicit non-claim language"):
        normalize_intake_record(_base_intake(claims_boundary="Validated compliance and remediation are complete."))


def test_intake_minimum_rejects_prohibited_assertion() -> None:
    with pytest.raises(ValueError, match="prohibited assertion"):
        normalize_intake_record(_base_intake(claims_boundary="No false claim, but CMMC_CERTIFIED is still prohibited text."))


def test_intake_minimum_rejects_reviewed_without_rationale() -> None:
    with pytest.raises(ValueError, match="reviewed intakes require review_rationale"):
        normalize_intake_record(_base_intake(human_review_status="REVIEWED_ACTION_REQUIRED"))


def test_intake_minimum_rejects_missing_downstream_route() -> None:
    with pytest.raises(ValueError, match="downstream_evidence or downstream_route is required"):
        normalize_intake_record(_base_intake(downstream_route=""))


def test_intake_minimum_rejects_duplicate_ids(tmp_path) -> None:
    intake_file = tmp_path / "intakes.json"
    _write_json(intake_file, {"intakes": [_base_intake(), _base_intake()]})

    with pytest.raises(ValueError, match="duplicate intake_id values"):
        build_intake_minimum_ledger(
            intake_file=intake_file,
            repository="Bdavis1390/Sara_pro",
            commit_sha="abc123",
            operator="github-actions",
        )
