#!/usr/bin/env python3
"""Negative test corpus for the WS-BOEING-01 external evidence transition guard.

Every fixture is intentionally invalid. PASS means the validator rejected every
attempt to close an external gate using a prohibited or incomplete substitute.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from validate_external_evidence_transition import validate_request


def base_request(gate: str, evidence_class: str) -> dict:
    return {
        "gate": gate,
        "proposed_state": "verified",
        "evidence_class": evidence_class,
        "external_authority": "Example External Authority",
        "authority_role": "Authorized reviewer or partner representative",
        "authorization_or_review_date": "2026-09-03",
        "source_identifier": "external:test-fixture",
        "source_digest_sha256": "a" * 64,
        "scope": "placeholder",
        "claims_allowed": ["test fixture only"],
        "claims_not_allowed": ["not real evidence"],
    }


def main() -> int:
    contract = json.loads(Path("boeing_spirit/external_evidence_transition_contract.v1.json").read_text())
    confidence = json.loads(Path("boeing_spirit/confidence.v1.json").read_text())
    current_states = {name: gate.get("status", "missing") for name, gate in confidence["gates"].items()}

    fixtures: list[tuple[str, dict, str]] = []

    r = base_request("partner_data_access", "AUTHORIZED_PARTNER_DATA_ACCESS")
    r.update({
        "scope": "partner authorization dataset or sandbox use rights classification handling boundary public dataset",
        "data_owner": "Example",
        "data_classification": "PUBLIC",
        "authorized_environment": "Example",
        "retention_or_deletion_terms": "Example",
    })
    fixtures.append(("reject-public-dataset-as-partner-data", r, "forbidden substitute"))

    r = base_request("partner_data_access", "AUTHORIZED_PARTNER_DATA_ACCESS")
    r.update({
        "external_authority": "Worldshepherd",
        "scope": "partner authorization dataset or sandbox use rights classification handling boundary",
        "data_owner": "Example",
        "data_classification": "PROPRIETARY",
        "authorized_environment": "Example",
        "retention_or_deletion_terms": "Example",
    })
    fixtures.append(("reject-internal-authority", r, "external_authority cannot be an internal/self authority"))

    r = base_request("measured_effect_size", "PARTNER_MEASURED_EFFECT")
    r.update({
        "source_digest_sha256": "",
        "scope": "predeclared endpoint baseline or comparator effect estimate uncertainty confounder review",
        "endpoint_id": "E1",
        "baseline_definition": "Example",
        "effect_estimate": "Example",
        "uncertainty_statement": "Example",
        "ground_truth_owner": "Example",
        "independent_review_reference": "Example",
    })
    fixtures.append(("reject-effect-without-digest", r, "missing required evidence field source_digest_sha256"))

    r = base_request("security_compliance_fit", "PARTNER_SECURITY_FIT_VALIDATION")
    r.update({
        "scope": "actual procurement or program applicable clauses data classification authorized environment assessment evidence public cybersecurity crosswalk",
        "procurement_or_program_id": "Example",
        "applicable_security_requirements": ["Example"],
        "data_classification": "Example",
        "authorized_environment": "Example",
        "assessment_or_partner_validation_reference": "Example",
    })
    fixtures.append(("reject-public-crosswalk-as-security-validation", r, "forbidden substitute"))

    r = base_request("partner_pilot", "AUTHORIZED_PARTNER_PILOT")
    r.update({
        "scope": "partner sponsor pilot scope execution record ground truth closeout synthetic pilot",
        "pilot_identifier": "Example",
        "partner_sponsor": "Example",
        "pilot_start": "2026-09-01",
        "pilot_end": "2026-09-02",
        "ground_truth_owner": "Example",
    })
    fixtures.append(("reject-synthetic-pilot-as-partner-pilot", r, "forbidden substitute"))

    r = base_request("independent_review", "QUALIFIED_INDEPENDENT_REVIEW")
    r.update({
        "external_authority": "Worldshepherd",
        "scope": "independent reviewer conflict disclosure reproducibility methodological review disposition",
        "reviewer_identity": "Worldshepherd",
        "reviewer_organization": "Worldshepherd",
        "reviewer_qualifications": "Internal",
        "conflict_disclosure": "Self review",
        "review_disposition": "PASS",
        "review_report_reference": "Example",
    })
    fixtures.append(("reject-self-independent-review", r, "external_authority cannot be an internal/self authority"))

    r = base_request("partner_data_access", "AUTHORIZED_PARTNER_DATA_ACCESS")
    r.update({
        "scope": "partner authorization only",
        "data_owner": "Example",
        "data_classification": "PROPRIETARY",
        "authorized_environment": "Example",
        "retention_or_deletion_terms": "Example",
    })
    fixtures.append(("reject-incomplete-scope", r, "scope missing required term"))

    results = []
    for name, req, expected_fragment in fixtures:
        errors = validate_request(deepcopy(req), contract, current_states)
        passed = bool(errors) and any(expected_fragment in error for error in errors)
        results.append({
            "fixture": name,
            "expected_rejection_fragment": expected_fragment,
            "rejected": bool(errors),
            "expected_rejection_observed": passed,
            "errors": errors,
        })

    report = {
        "schema": "WS-BOEING-SPIRIT-EXTERNAL-EVIDENCE-TRANSITION-NEGATIVE-TEST-V1",
        "evidence_class": "INTERNAL NEGATIVE GOVERNANCE TEST ONLY",
        "fixture_count": len(results),
        "all_invalid_transitions_rejected": all(r["rejected"] for r in results),
        "all_expected_rejection_reasons_observed": all(r["expected_rejection_observed"] for r in results),
        "result": "PASS" if all(r["rejected"] and r["expected_rejection_observed"] for r in results) else "FAIL",
        "results": results,
        "contact_gate_effect": "NONE",
        "claims_boundary": "PASS validates rejection behavior against intentionally invalid internal fixtures only. It does not validate any real external evidence, close any Boeing/Spirit gate, or authorize contact."
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
