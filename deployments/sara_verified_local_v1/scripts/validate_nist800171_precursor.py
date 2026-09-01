#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re

EXPECTED_FAMILIES = [
    "Access Control",
    "Awareness and Training",
    "Audit and Accountability",
    "Configuration Management",
    "Identification and Authentication",
    "Incident Response",
    "Maintenance",
    "Media Protection",
    "Personnel Security",
    "Physical Protection",
    "Planning",
    "Risk Assessment",
    "Security Assessment and Monitoring",
    "System and Communications Protection",
    "System and Information Integrity",
    "System and Services Acquisition",
    "Supply Chain Risk Management",
]
ALLOWED_STATUSES = {
    "INTERNAL_EVIDENCE_PARTIAL",
    "PROCEDURAL_ONLY",
    "EXTERNAL_EVIDENCE_REQUIRED",
    "UNVERIFIED",
}
FORBIDDEN_CLAIMS = [
    re.compile(r"\bCMMC\s+CERTIFIED\b", re.I),
    re.compile(r"\bNIST\s+(?:SP\s+)?800-171\s+COMPLIANT\b", re.I),
    re.compile(r"\bFULLY\s+IMPLEMENTED\b", re.I),
    re.compile(r"\bCUI\s+(?:PROCESSING\s+)?AUTHORIZED\b", re.I),
]


def load(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def require_nonempty(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"missing/nonempty string required: {label}")


def main() -> None:
    repo_root = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", pathlib.Path(__file__).resolve().parents[3]))
    boundary_path = repo_root / "security/nist800171/system-boundary.json"
    map_path = repo_root / "security/nist800171/ssp-evidence-map.json"
    out_dir = pathlib.Path(os.environ.get("NIST_PRECURSOR_EVIDENCE_DIR", repo_root / "nist800171_precursor_evidence"))
    out_dir.mkdir(parents=True, exist_ok=True)
    boundary = load(boundary_path)
    mapping = load(map_path)

    checks: dict[str, bool] = {}
    checks["standard_revision_exact"] = boundary.get("standard") == "NIST SP 800-171 Rev. 3" and mapping.get("standard") == "NIST SP 800-171 Rev. 3"
    checks["boundary_schema_exact"] = boundary.get("schema") == "WS-SARA-NIST800171-SYSTEM-BOUNDARY-V1"
    checks["map_schema_exact"] = mapping.get("schema") == "WS-SARA-NIST800171-SSP-EVIDENCE-MAP-V1"
    checks["cui_not_authorized"] = boundary.get("cui_scope_status") == "CUI_PROCESSING_NOT_AUTHORIZED_NOT_CURRENTLY_CLAIMED"
    checks["assessment_not_claimed"] = mapping.get("assessment_status") == "NOT_ASSESSED" and mapping.get("sprs_status") == "NOT_CLAIMED" and mapping.get("cmmc_status") == "NOT_CLAIMED" and mapping.get("ato_status") == "NOT_CLAIMED"
    checks["ssp_requirement_reference_present"] = mapping.get("system_security_plan_requirement_reference") == "03.15.02"
    checks["odp_status_explicit"] = isinstance(mapping.get("odp_status"), str) and "REQUIRES" in mapping["odp_status"]

    components = boundary.get("components")
    if not isinstance(components, list) or not components:
        raise SystemExit("boundary components required")
    component_ids: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            raise SystemExit("invalid component")
        for field in ("id", "name", "trust_zone", "identity", "persistence"):
            require_nonempty(component.get(field), f"component.{field}")
        cid = component["id"]
        if cid in component_ids:
            raise SystemExit(f"duplicate component id: {cid}")
        component_ids.add(cid)
        if component.get("in_boundary") is not True:
            raise SystemExit(f"component not explicitly in boundary: {cid}")
        if not isinstance(component.get("data_role"), list) or not component["data_role"]:
            raise SystemExit(f"component data role missing: {cid}")
        if not isinstance(component.get("security_properties"), list) or not component["security_properties"]:
            raise SystemExit(f"component security properties missing: {cid}")
    checks["boundary_components_complete"] = len(component_ids) >= 4

    external_entities = boundary.get("external_entities")
    if not isinstance(external_entities, list):
        raise SystemExit("external_entities required")
    external_ids = {e.get("id") for e in external_entities if isinstance(e, dict)}
    if None in external_ids:
        raise SystemExit("external entity id missing")
    valid_endpoints = component_ids | external_ids

    data_classes = boundary.get("data_classes")
    if not isinstance(data_classes, list) or not data_classes:
        raise SystemExit("data_classes required")
    data_ids = {d.get("id") for d in data_classes if isinstance(d, dict)}
    if "cui" not in data_ids:
        raise SystemExit("explicit CUI data class required")
    cui_record = next(d for d in data_classes if isinstance(d, dict) and d.get("id") == "cui")
    checks["cui_data_class_fail_closed"] = cui_record.get("cui") is True and cui_record.get("status") == "NOT_AUTHORIZED_NOT_CURRENTLY_CLAIMED"

    interfaces = boundary.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        raise SystemExit("interfaces required")
    interface_ids: set[str] = set()
    for interface in interfaces:
        if not isinstance(interface, dict):
            raise SystemExit("invalid interface")
        for field in ("id", "source", "destination", "protocol", "direction", "authorization"):
            require_nonempty(interface.get(field), f"interface.{field}")
        iid = interface["id"]
        if iid in interface_ids:
            raise SystemExit(f"duplicate interface id: {iid}")
        interface_ids.add(iid)
        if interface["source"] not in valid_endpoints or interface["destination"] not in valid_endpoints:
            raise SystemExit(f"invalid interface endpoint: {iid}")
        classes = interface.get("data_classes")
        if not isinstance(classes, list) or not classes or any(c not in data_ids for c in classes):
            raise SystemExit(f"invalid data class reference: {iid}")
    checks["interfaces_referentially_valid"] = True

    exclusions = boundary.get("explicit_exclusions")
    checks["external_exclusions_explicit"] = isinstance(exclusions, list) and len(exclusions) >= 8

    families = mapping.get("families")
    if not isinstance(families, list):
        raise SystemExit("families required")
    names = [f.get("family") for f in families if isinstance(f, dict)]
    checks["all_17_families_exact_once"] = names == EXPECTED_FAMILIES and len(set(names)) == 17
    if not checks["all_17_families_exact_once"]:
        raise SystemExit("17 NIST families must appear exactly once in required order")

    for family in families:
        name = family["family"]
        if family.get("status") not in ALLOWED_STATUSES:
            raise SystemExit(f"invalid family status: {name}")
        require_nonempty(family.get("owner"), f"family owner: {name}")
        require_nonempty(family.get("evidence_summary"), f"evidence summary: {name}")
        require_nonempty(family.get("odp_status"), f"ODP status: {name}")
        refs = family.get("evidence_refs")
        gaps = family.get("gaps")
        if not isinstance(refs, list) or not isinstance(gaps, list) or not gaps:
            raise SystemExit(f"evidence refs/gaps invalid: {name}")
        for ref in refs:
            require_nonempty(ref, f"evidence ref: {name}")
            target = repo_root / ref
            if not target.is_file():
                raise SystemExit(f"repository evidence ref does not exist: {name}: {ref}")
    checks["family_owners_gaps_odps_complete"] = True
    checks["repo_evidence_refs_resolve"] = True

    serialized = boundary_path.read_text(encoding="utf-8") + "\n" + map_path.read_text(encoding="utf-8")
    forbidden_hits = [pattern.pattern for pattern in FORBIDDEN_CLAIMS if pattern.search(serialized)]
    checks["unsupported_compliance_claims_absent"] = not forbidden_hits

    require_nonempty(boundary.get("claims_boundary"), "boundary claims_boundary")
    require_nonempty(mapping.get("claims_boundary"), "map claims_boundary")
    checks["claims_boundaries_present"] = True

    result = "PASS" if all(checks.values()) else "FAIL"
    record = {
        "schema": "WS-SARA-NIST800171-SSP-PRECURSOR-EVIDENCE-V1",
        "result": result,
        "evidence_status": "INTERNAL_STRUCTURAL_AND_EVIDENCE_MAPPING_PRECURSOR",
        "source_commit_sha": os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "standard": "NIST SP 800-171 Rev. 3",
        "cui_scope_status": boundary["cui_scope_status"],
        "assessment_status": mapping["assessment_status"],
        "family_count": len(families),
        "checks": checks,
        "input_sha256": {
            "system-boundary.json": "sha256:" + hashlib.sha256(boundary_path.read_bytes()).hexdigest(),
            "ssp-evidence-map.json": "sha256:" + hashlib.sha256(map_path.read_bytes()).hexdigest(),
        },
        "forbidden_claim_hits": forbidden_hits,
        "claims_boundary": "PASS means the precursor documents are structurally complete, internally evidence-linked, and fail closed against unsupported compliance claims. It is not an 800-171A assessment, approved SSP, SPRS score, CMMC certification, ATO, or CUI authorization."
    }
    out_path = out_dir / "nist800171-ssp-precursor-evidence.json"
    out_path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if result != "PASS":
        raise SystemExit("NIST800171_PRECURSOR_FAIL: " + json.dumps(checks, sort_keys=True))
    print("NIST800171_PRECURSOR_PASS", record["source_commit_sha"])


if __name__ == "__main__":
    main()
