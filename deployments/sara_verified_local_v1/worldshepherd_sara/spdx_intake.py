from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any

SPDX_INTAKE_SCHEMA = "WS-SPDX-INTAKE-EVIDENCE-V1"
SPDX_CONTEXT_301 = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
SPDX_SPEC_VERSION = "3.0.1"
SOFTWARE_SBOM_TYPE = "software_Sbom"
SOFTWARE_PACKAGE_TYPE = "software_Package"
SOFTWARE_PACKAGE_VERSION = "software_packageVersion"
SOFTWARE_PACKAGE_URL = "software_packageUrl"

CLAIMS_BOUNDARY = (
    "This adapter performs bounded local integrity, shape, identifier, and reference checks over an input SPDX 3.0.1 "
    "JSON-LD document while preserving the source as authoritative. It does not perform the SPDX JSON Schema or "
    "OWL/SHACL semantic validations required for SPDX conformance and does not establish license conclusions, legal "
    "review, supplier approval, software admission, release approval, completeness, external validation, or certification."
)


@dataclass(frozen=True)
class SPDXIntakeDecision:
    schema: str
    status: str
    ready_for_human_admission_review: bool
    source_canonical_sha256: str
    graph_element_count: int
    spdx_document_count: int
    sbom_count: int
    package_count: int
    relationship_count: int
    package_refs: list[dict[str, str | None]]
    reasons: list[str]
    source_document_modified: bool
    spdx_conformance_established: bool
    json_schema_validation_established: bool
    semantic_ontology_validation_established: bool
    complete_sbom_established: bool
    license_legal_review_established: bool
    supplier_approval_established: bool
    admission_authorized: bool
    release_approved: bool
    external_validation_established: bool
    claims_boundary: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return f"sha256:{sha256(canonical_json_bytes(value)).hexdigest()}"


def _context_contains_301(context: Any) -> bool:
    if context == SPDX_CONTEXT_301:
        return True
    if isinstance(context, list):
        return SPDX_CONTEXT_301 in context
    return False


def _element_id(element: dict[str, Any]) -> str | None:
    value = element.get("spdxId", element.get("@id"))
    return value if isinstance(value, str) and value else None


def _type_values(element: dict[str, Any]) -> set[str]:
    raw = element.get("type", element.get("@type"))
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {value for value in raw if isinstance(value, str)}
    return set()


def _refs(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _require_element_fields(element: dict[str, Any], element_type: str, reasons: list[str]) -> None:
    element_id = _element_id(element) or f"<{element_type}:missing-id>"
    if _element_id(element) is None:
        reasons.append(f"{element_type} missing spdxId/@id: {element_id}")
    if not element.get("creationInfo"):
        reasons.append(f"{element_type} missing creationInfo: {element_id}")


def evaluate_spdx301_document(document: dict[str, Any]) -> SPDXIntakeDecision:
    if not isinstance(document, dict):
        raise TypeError("SPDX input must be a JSON object")

    before = canonical_sha256(document)
    reasons: list[str] = []

    if not _context_contains_301(document.get("@context")):
        reasons.append("official SPDX 3.0.1 JSON-LD context is missing")

    graph = document.get("@graph")
    if not isinstance(graph, list) or not graph:
        reasons.append("@graph must be a non-empty list")
        graph = []

    typed_graph: list[tuple[dict[str, Any], set[str]]] = []
    for index, raw in enumerate(graph):
        if not isinstance(raw, dict):
            reasons.append(f"@graph element {index} is not an object")
            continue
        typed_graph.append((raw, _type_values(raw)))

    spdx_documents = [item for item, types in typed_graph if "SpdxDocument" in types]
    sboms = [item for item, types in typed_graph if SOFTWARE_SBOM_TYPE in types]
    packages = [item for item, types in typed_graph if SOFTWARE_PACKAGE_TYPE in types]
    relationships = [item for item, types in typed_graph if "Relationship" in types]
    creation_infos = [item for item, types in typed_graph if "CreationInfo" in types]

    if len(spdx_documents) != 1:
        reasons.append(f"expected exactly one SpdxDocument, found {len(spdx_documents)}")
    if not sboms:
        reasons.append(f"no {SOFTWARE_SBOM_TYPE} element found")
    if not packages:
        reasons.append(f"no {SOFTWARE_PACKAGE_TYPE} element found")
    if not creation_infos:
        reasons.append("no CreationInfo element found")
    elif not any(info.get("specVersion") == SPDX_SPEC_VERSION for info in creation_infos):
        reasons.append("no CreationInfo declares specVersion 3.0.1")

    ids: list[str] = []
    for element, types in typed_graph:
        element_id = _element_id(element)
        if element_id:
            ids.append(element_id)
        if "SpdxDocument" in types:
            _require_element_fields(element, "SpdxDocument", reasons)
        if SOFTWARE_SBOM_TYPE in types:
            _require_element_fields(element, SOFTWARE_SBOM_TYPE, reasons)
        if SOFTWARE_PACKAGE_TYPE in types:
            _require_element_fields(element, SOFTWARE_PACKAGE_TYPE, reasons)
            if not isinstance(element.get("name"), str):
                reasons.append(f"{SOFTWARE_PACKAGE_TYPE} missing name: {element_id or '<missing-id>'}")
        if "Relationship" in types:
            _require_element_fields(element, "Relationship", reasons)

    seen: set[str] = set()
    duplicates: set[str] = set()
    for element_id in ids:
        if element_id in seen:
            duplicates.add(element_id)
        seen.add(element_id)
    for duplicate in sorted(duplicates):
        reasons.append(f"duplicate SPDX identifier: {duplicate}")

    id_set = set(ids)
    for collection in [*spdx_documents, *sboms]:
        collection_id = _element_id(collection) or "<missing-id>"
        for field in ("element", "rootElement"):
            for ref in _refs(collection.get(field)):
                if ref not in id_set:
                    reasons.append(f"unresolved {field} reference from {collection_id}: {ref}")

    package_refs: list[dict[str, str | None]] = []
    for package in packages:
        package_refs.append(
            {
                "spdx_id": _element_id(package),
                "name": package.get("name") if isinstance(package.get("name"), str) else None,
                "version": (
                    package.get(SOFTWARE_PACKAGE_VERSION)
                    if isinstance(package.get(SOFTWARE_PACKAGE_VERSION), str)
                    else None
                ),
                "purl": (
                    package.get(SOFTWARE_PACKAGE_URL)
                    if isinstance(package.get(SOFTWARE_PACKAGE_URL), str)
                    else None
                ),
            }
        )
    package_refs.sort(key=lambda item: (item.get("name") or "", item.get("version") or "", item.get("spdx_id") or ""))

    after = canonical_sha256(document)
    source_modified = before != after
    if source_modified:
        reasons.append("source document changed during intake evaluation")

    ready = not reasons
    return SPDXIntakeDecision(
        schema=SPDX_INTAKE_SCHEMA,
        status="READY_FOR_HUMAN_ADMISSION_REVIEW" if ready else "BLOCKED_SPDX_INTAKE",
        ready_for_human_admission_review=ready,
        source_canonical_sha256=before,
        graph_element_count=len(graph),
        spdx_document_count=len(spdx_documents),
        sbom_count=len(sboms),
        package_count=len(packages),
        relationship_count=len(relationships),
        package_refs=package_refs,
        reasons=sorted(set(reasons)),
        source_document_modified=source_modified,
        spdx_conformance_established=False,
        json_schema_validation_established=False,
        semantic_ontology_validation_established=False,
        complete_sbom_established=False,
        license_legal_review_established=False,
        supplier_approval_established=False,
        admission_authorized=False,
        release_approved=False,
        external_validation_established=False,
        claims_boundary=CLAIMS_BOUNDARY,
    )


def intake_record(decision: SPDXIntakeDecision) -> dict[str, Any]:
    return asdict(decision)
