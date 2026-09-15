#!/usr/bin/env python3
"""Fail-closed validator for WS-BOEING-01 external evidence transitions.

The default branch state contains no requested transitions. Future transition
requests must provide a gate-specific external evidence envelope; preparation,
synthetic, public, CI, or self-review artifacts cannot close external gates.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CLOSED = {"complete", "verified"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def validate_request(req: dict, contract: dict, current_states: dict[str, str]) -> list[str]:
    errors: list[str] = []
    gate = req.get("gate")
    gate_contracts = {x.get("gate"): x for x in contract.get("gate_contracts", [])}
    gc = gate_contracts.get(gate)
    if not gc:
        return [f"unknown gate: {gate!r}"]
    if current_states.get(gate) in CLOSED:
        errors.append(f"{gate}: current gate already closed; transition request is not an open->closed transition")
    if req.get("proposed_state") not in CLOSED:
        errors.append(f"{gate}: proposed_state must be complete or verified")

    for field in contract.get("evidence_envelope_required_fields", []):
        value = req.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"{gate}: missing required evidence field {field}")

    if req.get("evidence_class") not in set(gc.get("allowed_evidence_classes", [])):
        errors.append(f"{gate}: evidence_class not allowed for this gate")
    digest = str(req.get("source_digest_sha256", ""))
    if digest and not SHA256_RE.fullmatch(digest):
        errors.append(f"{gate}: source_digest_sha256 must be 64 lowercase hex characters")

    for field in gc.get("required_additional_fields", []):
        value = req.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"{gate}: missing gate-specific field {field}")

    scope = str(req.get("scope", "")).lower()
    for term in gc.get("required_scope_terms", []):
        if term.lower() not in scope:
            errors.append(f"{gate}: scope missing required term {term!r}")

    serialized = json.dumps(req, sort_keys=True).lower()
    for forbidden in gc.get("forbidden_substitutes", []):
        if forbidden.lower() in serialized:
            errors.append(f"{gate}: forbidden substitute appears in transition evidence: {forbidden!r}")

    authority = str(req.get("external_authority", "")).strip().lower()
    if authority in {"worldshepherd", "sara", "cre1aws", "internal", "self"}:
        errors.append(f"{gate}: external_authority cannot be an internal/self authority")
    if gate == "independent_review":
        reviewer = str(req.get("reviewer_identity", "")).strip().lower()
        if not reviewer or reviewer == authority == "worldshepherd":
            errors.append("independent_review: reviewer identity must be genuinely external")

    if not isinstance(req.get("claims_allowed"), list) or not isinstance(req.get("claims_not_allowed"), list):
        errors.append(f"{gate}: claims_allowed and claims_not_allowed must be lists")
    elif not req.get("claims_not_allowed"):
        errors.append(f"{gate}: claims_not_allowed must remain explicit")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default="boeing_spirit/external_evidence_transition_contract.v1.json")
    ap.add_argument("--confidence", default="boeing_spirit/confidence.v1.json")
    ap.add_argument("--output", default="boeing_spirit/evidence/external-evidence-transition-report.json")
    args = ap.parse_args()

    contract = load(args.contract)
    confidence = load(args.confidence)
    errors: list[str] = []

    if contract.get("schema") != "WS-BOEING-SPIRIT-EXTERNAL-EVIDENCE-TRANSITION-CONTRACT-V1":
        errors.append("unexpected contract schema")
    if contract.get("default_rule") != "DENY_TRANSITION_WITHOUT_EXTERNAL_EVIDENCE":
        errors.append("default transition rule must deny unsupported transitions")
    if not str(contract.get("contact_gate_effect", "")).startswith("NONE"):
        errors.append("transition contract itself must have zero contact-gate effect")

    required = set(confidence.get("required_for_contact", []))
    contracts = contract.get("gate_contracts", [])
    contract_gates = {x.get("gate") for x in contracts}
    if contract_gates != required:
        errors.append(f"gate contract set {sorted(contract_gates)} != required contact gates {sorted(required)}")
    if len(contracts) != len(contract_gates):
        errors.append("duplicate gate contracts detected")

    current_states = {name: gate.get("status", "missing") for name, gate in confidence.get("gates", {}).items()}
    requests = contract.get("current_transition_requests", [])
    if not isinstance(requests, list):
        errors.append("current_transition_requests must be a list")
        requests = []
    for i, req in enumerate(requests):
        if not isinstance(req, dict):
            errors.append(f"transition request {i}: expected object")
            continue
        errors.extend(validate_request(req, contract, current_states))

    expected = "NO_TRANSITIONS_REQUESTED" if not requests else "TRANSITIONS_REQUIRE_VALID_EXTERNAL_EVIDENCE"
    if contract.get("current_expected_result") != expected:
        errors.append("current_expected_result does not match request state")

    report = {
        "schema": "WS-BOEING-SPIRIT-EXTERNAL-EVIDENCE-TRANSITION-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "transition_request_count": len(requests),
        "current_expected_result": expected,
        "required_gate_count": len(required),
        "required_gates": sorted(required),
        "all_external_gate_states_before_requests": {gate: current_states.get(gate, "missing") for gate in sorted(required)},
        "closed_gate_transitions_authorized_by_this_report": 0 if not requests else (len(requests) if not errors else 0),
        "contact_gate_effect": "NONE" if not requests else "REQUIRES_SEPARATE_CONFIDENCE_RECALCULATION_AFTER_VERIFIED_TRANSITION",
        "claims_boundary": (
            "PASS with zero transition requests validates the fail-closed transition contract only and closes no Boeing/Spirit external gate. "
            "A future accepted envelope would authorize only the specified evidence-state transition for subsequent confidence recalculation; it would not by itself authorize contact unless the complete contact gate also passes."
        ),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
