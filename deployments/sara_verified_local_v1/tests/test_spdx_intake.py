from copy import deepcopy

from worldshepherd_sara.spdx_intake import (
    SPDX_CONTEXT_301,
    SPDX_INTAKE_SCHEMA,
    canonical_sha256,
    evaluate_spdx301_document,
)


def sample_document():
    return {
        "@context": SPDX_CONTEXT_301,
        "@graph": [
            {
                "type": "CreationInfo",
                "@id": "_:creationinfo",
                "specVersion": "3.0.1",
                "createdBy": ["urn:worldshepherd:test-agent"],
                "created": "2026-09-16T20:00:00Z",
            },
            {
                "type": "SpdxDocument",
                "spdxId": "urn:worldshepherd:spdx:document:001",
                "creationInfo": "_:creationinfo",
                "rootElement": ["urn:worldshepherd:spdx:sbom:001"],
                "element": [
                    "urn:worldshepherd:spdx:sbom:001",
                    "urn:worldshepherd:spdx:package:001",
                ],
                "name": "Worldshepherd SPDX intake fixture",
            },
            {
                "type": "Sbom",
                "spdxId": "urn:worldshepherd:spdx:sbom:001",
                "creationInfo": "_:creationinfo",
                "rootElement": ["urn:worldshepherd:spdx:package:001"],
                "element": ["urn:worldshepherd:spdx:package:001"],
            },
            {
                "type": "Package",
                "spdxId": "urn:worldshepherd:spdx:package:001",
                "creationInfo": "_:creationinfo",
                "name": "example-package",
                "packageVersion": "1.2.3",
                "packageUrl": "pkg:pypi/example-package@1.2.3",
            },
        ],
    }


def test_review_ready_intake_preserves_source_and_never_confers_authority():
    document = sample_document()
    before = deepcopy(document)
    decision = evaluate_spdx301_document(document)

    assert decision.schema == SPDX_INTAKE_SCHEMA
    assert decision.status == "READY_FOR_HUMAN_ADMISSION_REVIEW"
    assert decision.ready_for_human_admission_review is True
    assert decision.spdx_document_count == 1
    assert decision.sbom_count == 1
    assert decision.package_count == 1
    assert decision.package_refs == [
        {
            "spdx_id": "urn:worldshepherd:spdx:package:001",
            "name": "example-package",
            "version": "1.2.3",
            "purl": "pkg:pypi/example-package@1.2.3",
        }
    ]
    assert document == before
    assert decision.source_document_modified is False
    assert decision.spdx_conformance_established is False
    assert decision.json_schema_validation_established is False
    assert decision.semantic_ontology_validation_established is False
    assert decision.complete_sbom_established is False
    assert decision.license_legal_review_established is False
    assert decision.supplier_approval_established is False
    assert decision.admission_authorized is False
    assert decision.release_approved is False
    assert decision.external_validation_established is False


def test_canonical_digest_is_order_independent_for_json_object_keys():
    document = sample_document()
    reordered = {"@graph": document["@graph"], "@context": document["@context"]}
    assert canonical_sha256(document) == canonical_sha256(reordered)


def test_wrong_context_fails_closed():
    document = sample_document()
    document["@context"] = "https://example.invalid/context"
    decision = evaluate_spdx301_document(document)
    assert decision.status == "BLOCKED_SPDX_INTAKE"
    assert "official SPDX 3.0.1 JSON-LD context is missing" in decision.reasons


def test_multiple_spdx_documents_fail_closed():
    document = sample_document()
    duplicate = deepcopy(document["@graph"][1])
    duplicate["spdxId"] = "urn:worldshepherd:spdx:document:002"
    document["@graph"].append(duplicate)
    decision = evaluate_spdx301_document(document)
    assert "expected exactly one SpdxDocument, found 2" in decision.reasons


def test_duplicate_identifier_fails_closed():
    document = sample_document()
    duplicate = deepcopy(document["@graph"][3])
    duplicate["name"] = "duplicate-package"
    document["@graph"].append(duplicate)
    decision = evaluate_spdx301_document(document)
    assert "duplicate SPDX identifier: urn:worldshepherd:spdx:package:001" in decision.reasons


def test_dangling_collection_reference_fails_closed():
    document = sample_document()
    document["@graph"][2]["element"].append("urn:worldshepherd:spdx:package:missing")
    decision = evaluate_spdx301_document(document)
    assert any(reason.startswith("unresolved element reference") for reason in decision.reasons)


def test_package_without_name_fails_closed():
    document = sample_document()
    document["@graph"][3].pop("name")
    decision = evaluate_spdx301_document(document)
    assert "Package missing name: urn:worldshepherd:spdx:package:001" in decision.reasons


def test_wrong_creation_info_spec_version_fails_closed():
    document = sample_document()
    document["@graph"][0]["specVersion"] = "3.0.0"
    decision = evaluate_spdx301_document(document)
    assert "no CreationInfo declares specVersion 3.0.1" in decision.reasons


def test_missing_package_fails_closed():
    document = sample_document()
    document["@graph"] = document["@graph"][:3]
    document["@graph"][1]["element"] = ["urn:worldshepherd:spdx:sbom:001"]
    document["@graph"][2]["element"] = []
    document["@graph"][2]["rootElement"] = []
    decision = evaluate_spdx301_document(document)
    assert "no Package element found" in decision.reasons


def test_non_object_input_rejected():
    try:
        evaluate_spdx301_document([])  # type: ignore[arg-type]
    except TypeError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("non-object SPDX input should fail")
