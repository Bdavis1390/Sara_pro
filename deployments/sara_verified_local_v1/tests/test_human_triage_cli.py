from __future__ import annotations

import json

import pytest

from worldshepherd_sara.human_triage_cli import (
    DECISION_ACCEPTED_RISK,
    DECISION_NOT_APPLICABLE,
    DECISION_PATCH_REQUIRED,
    EVIDENCE_STATUS,
    REVIEW_INPUT_NONE,
    REVIEW_INPUT_SUPPLIED,
    TRIAGE_LEDGER_SCHEMA,
    build_human_triage_ledger,
    main,
    write_human_triage_ledger,
)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _make_vulnerability_evidence(tmp_path, *, with_advisory: bool = True):
    root = tmp_path / "vulnerability_evidence_ci"
    records = []
    if with_advisory:
        records = [
            {
                "advisory_id": "CVE-2099-0001",
                "component": "fastapi",
                "severity": "HIGH",
                "source": "test-advisory-input",
                "reference": "https://example.invalid/CVE-2099-0001",
                "matched_component_in_sbom": True,
                "triage_status": "OPEN_TRIAGE_REQUIRED",
                "remediation_status": "NOT_REMEDIATED_BY_THIS_RECORD",
            },
            {
                "advisory_id": "CVE-2099-0002",
                "component": "unused-package",
                "severity": "LOW",
                "source": "test-advisory-input",
                "reference": "https://example.invalid/CVE-2099-0002",
                "matched_component_in_sbom": False,
                "triage_status": "NOT_PRESENT_IN_CURRENT_SBOM_INPUT",
                "remediation_status": "NOT_REMEDIATED_BY_THIS_RECORD",
            },
        ]
    _write_json(
        root / "vulnerability-advisory-report.json",
        {
            "schema": "WS-VULNERABILITY-ADVISORY-EVIDENCE-V1",
            "generated_utc": "2026-09-01T18:00:00Z",
            "repository": "Bdavis1390/Sara_pro",
            "commit_sha": "abc123",
            "operator": "github-actions",
            "evidence_status": "INTERNAL_CI_GENERATED_UNSIGNED",
            "advisory_input_status": "ADVISORY_INPUT_RECORDED_UNVERIFIED" if with_advisory else "NO_EXTERNAL_ADVISORY_FEED_EXECUTED",
            "advisory_triage": {
                "advisory_record_count": len(records),
                "matched_advisory_count": sum(1 for record in records if record["matched_component_in_sbom"]),
                "records": records,
            },
            "claims_boundary": "Vulnerability advisory evidence does not establish absence of vulnerabilities or remediation.",
        },
    )
    _write_json(
        root / "vulnerability-evidence-summary.json",
        {
            "schema": "WS-VULNERABILITY-ADVISORY-EVIDENCE-V1",
            "generated_utc": "2026-09-01T18:00:00Z",
            "repository": "Bdavis1390/Sara_pro",
            "commit_sha": "abc123",
            "operator": "github-actions",
            "evidence_status": "INTERNAL_CI_GENERATED_UNSIGNED",
            "advisory_input_status": "ADVISORY_INPUT_RECORDED_UNVERIFIED" if with_advisory else "NO_EXTERNAL_ADVISORY_FEED_EXECUTED",
            "component_count": 1,
            "advisory_record_count": len(records),
            "matched_advisory_count": sum(1 for record in records if record["matched_component_in_sbom"]),
            "vulnerability_report_sha256": "sha256:" + "1" * 64,
            "claims_boundary": "Vulnerability advisory evidence does not establish absence of vulnerabilities or remediation.",
        },
    )
    return root / "vulnerability-advisory-report.json", root / "vulnerability-evidence-summary.json"


def test_human_triage_records_pending_and_not_applicable_decisions(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)

    ledger, summary = build_human_triage_ledger(
        vulnerability_report=report_path,
        vulnerability_summary=summary_path,
        review_input=None,
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        operator="github-actions",
        executed_utc="2026-09-01T18:05:00Z",
    )

    assert ledger["schema"] == TRIAGE_LEDGER_SCHEMA
    assert ledger["evidence_status"] == EVIDENCE_STATUS
    assert ledger["review_input_status"] == REVIEW_INPUT_NONE
    assert ledger["review_summary"]["overall_status"] == "HUMAN_REVIEW_PENDING"
    assert ledger["review_summary"]["ledger_record_count"] == 2
    assert ledger["review_summary"]["human_review_required_count"] == 1
    assert ledger["review_summary"]["pending_review_count"] == 1
    assert ledger["review_summary"]["not_applicable_count"] == 1
    assert ledger["records"][0]["advisory_id"] == "CVE-2099-0001"
    assert ledger["records"][0]["decision"] == "PENDING_HUMAN_REVIEW"
    assert ledger["records"][0]["remediation_status"] == "NOT_RECORDED_BY_THIS_LEDGER"
    assert ledger["records"][1]["decision"] == DECISION_NOT_APPLICABLE
    assert summary["schema"] == TRIAGE_LEDGER_SCHEMA
    assert summary["pending_review_count"] == 1
    assert summary["summary_digest"].startswith("sha256:")
    assert "does not establish absence of vulnerabilities" in summary["claims_boundary"]
    assert "remediation completion" in summary["claims_boundary"]


def test_human_triage_applies_review_input_without_claiming_remediation(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)
    review_input = tmp_path / "reviews.json"
    _write_json(
        review_input,
        {
            "reviews": [
                {
                    "advisory_id": "CVE-2099-0001",
                    "decision": "PATCH_REQUIRED",
                    "reviewer": "CRE1AWS",
                    "rationale": "Matched component requires an explicit patch plan and evidence bundle before closure.",
                    "reviewed_utc": "2026-09-01T18:10:00Z",
                    "evidence_refs": ["vulnerability-advisory-report.json#CVE-2099-0001"],
                }
            ]
        },
    )

    ledger, summary = build_human_triage_ledger(
        vulnerability_report=report_path,
        vulnerability_summary=summary_path,
        review_input=review_input,
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        operator="CRE1AWS",
        executed_utc="2026-09-01T18:11:00Z",
    )

    assert ledger["review_input_status"] == REVIEW_INPUT_SUPPLIED
    assert ledger["review_summary"]["overall_status"] == "HUMAN_REVIEW_RECORDED_UNSIGNED"
    assert ledger["review_summary"]["patch_required_count"] == 1
    assert ledger["review_summary"]["pending_review_count"] == 0
    reviewed = next(record for record in ledger["records"] if record["advisory_id"] == "CVE-2099-0001")
    assert reviewed["decision"] == DECISION_PATCH_REQUIRED
    assert reviewed["reviewer"] == "CRE1AWS"
    assert reviewed["rationale"].startswith("Matched component requires")
    assert reviewed["remediation_status"] == "NOT_RECORDED_BY_THIS_LEDGER"
    assert summary["patch_required_count"] == 1
    text = json.dumps(ledger).lower()
    for forbidden in ("remediation_complete", "cmmc_certified", "partner_validated", "scan_passed"):
        assert forbidden not in text


def test_human_triage_supports_no_advisory_records(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=False)

    ledger, summary = build_human_triage_ledger(
        vulnerability_report=report_path,
        vulnerability_summary=summary_path,
        review_input=None,
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        operator="github-actions",
        executed_utc="2026-09-01T18:12:00Z",
    )

    assert ledger["review_summary"]["overall_status"] == "NO_ADVISORY_RECORDS"
    assert ledger["records"] == []
    assert summary["ledger_record_count"] == 0
    assert summary["human_review_required_count"] == 0


def test_human_triage_cli_writes_ledger_and_summary(tmp_path, monkeypatch) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)
    out_dir = tmp_path / "human_triage_ci"

    monkeypatch.chdir(tmp_path)
    exit_code = main(
        [
            "--vulnerability-report",
            str(report_path.relative_to(tmp_path)),
            "--vulnerability-summary",
            str(summary_path.relative_to(tmp_path)),
            "--out",
            str(out_dir.relative_to(tmp_path)),
            "--repository",
            "Bdavis1390/Sara_pro",
            "--commit-sha",
            "abc123",
            "--operator",
            "github-actions",
            "--executed-utc",
            "2026-09-01T18:13:00Z",
        ]
    )

    assert exit_code == 0
    ledger = json.loads((out_dir / "human-triage-ledger.json").read_text(encoding="utf-8"))
    summary = json.loads((out_dir / "human-triage-summary.json").read_text(encoding="utf-8"))
    assert ledger["schema"] == TRIAGE_LEDGER_SCHEMA
    assert summary["human_triage_ledger_sha256"].startswith("sha256:")
    assert summary["input_files"]["vulnerability_report"]["sha256"].startswith("sha256:")


def test_human_triage_rejects_unknown_review_advisory(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)
    review_input = tmp_path / "reviews.json"
    _write_json(
        review_input,
        {
            "reviews": [
                {
                    "advisory_id": "CVE-2099-9999",
                    "decision": "ACCEPTED_RISK",
                    "reviewer": "CRE1AWS",
                    "rationale": "Unknown advisory should be rejected.",
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="unknown advisory_id"):
        build_human_triage_ledger(
            vulnerability_report=report_path,
            vulnerability_summary=summary_path,
            review_input=review_input,
            repository="Bdavis1390/Sara_pro",
            commit_sha="abc123",
            operator="CRE1AWS",
        )


def test_human_triage_rejects_disallowed_review_decision(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)
    review_input = tmp_path / "reviews.json"
    _write_json(
        review_input,
        {
            "reviews": [
                {
                    "advisory_id": "CVE-2099-0001",
                    "decision": "REMEDIATION_COMPLETE",
                    "reviewer": "CRE1AWS",
                    "rationale": "This would make a false closure claim.",
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="decision must be one of"):
        build_human_triage_ledger(
            vulnerability_report=report_path,
            vulnerability_summary=summary_path,
            review_input=review_input,
            repository="Bdavis1390/Sara_pro",
            commit_sha="abc123",
            operator="CRE1AWS",
        )


def test_human_triage_rejects_bad_source_schema(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)
    _write_json(report_path, {"schema": "WRONG"})

    with pytest.raises(ValueError, match="unexpected vulnerability advisory report schema"):
        build_human_triage_ledger(
            vulnerability_report=report_path,
            vulnerability_summary=summary_path,
            review_input=None,
            repository="Bdavis1390/Sara_pro",
            commit_sha="abc123",
            operator="github-actions",
        )


def test_human_triage_rejects_paths_outside_working_directory(tmp_path, monkeypatch) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=False)
    outside = tmp_path.parent / "outside-vulnerability-summary.json"
    outside.write_text(summary_path.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="CLI path must resolve under working directory"):
        main(
            [
                "--vulnerability-report",
                str(report_path.relative_to(tmp_path)),
                "--vulnerability-summary",
                str(outside),
                "--out",
                "human_triage_ci",
                "--repository",
                "Bdavis1390/Sara_pro",
                "--commit-sha",
                "abc123",
            ]
        )


def test_write_human_triage_summary_contains_ledger_digest(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)

    summary = write_human_triage_ledger(
        out_dir=tmp_path / "human_triage_ci",
        vulnerability_report=report_path,
        vulnerability_summary=summary_path,
        review_input=None,
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        operator="github-actions",
    )

    assert summary["human_triage_ledger_path"].endswith("human-triage-ledger.json")
    assert summary["human_triage_ledger_sha256"].startswith("sha256:")
    assert summary["summary_digest"].startswith("sha256:")


def test_human_triage_accepts_accepted_risk_decision_with_rationale(tmp_path) -> None:
    report_path, summary_path = _make_vulnerability_evidence(tmp_path, with_advisory=True)
    review_input = tmp_path / "reviews.json"
    _write_json(
        review_input,
        {
            "reviews": [
                {
                    "advisory_id": "CVE-2099-0001",
                    "decision": "ACCEPTED_RISK",
                    "reviewer": "CRE1AWS",
                    "rationale": "Accepted for bounded prototype only; must be revisited before external release.",
                    "evidence_refs": ["risk-register#RISK-001"],
                }
            ]
        },
    )

    ledger, summary = build_human_triage_ledger(
        vulnerability_report=report_path,
        vulnerability_summary=summary_path,
        review_input=review_input,
        repository="Bdavis1390/Sara_pro",
        commit_sha="abc123",
        operator="CRE1AWS",
    )

    assert ledger["review_summary"]["accepted_risk_count"] == 1
    assert summary["accepted_risk_count"] == 1
    assert next(record for record in ledger["records"] if record["advisory_id"] == "CVE-2099-0001")[
        "decision"
    ] == DECISION_ACCEPTED_RISK
