from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def project_synthetic_manual_to_xml(fixture: dict[str, Any]) -> str:
    """Project the frozen synthetic manual into a simple XML interchange form.

    This output is intentionally NOT claimed as S1000D/MIL-standard compliant.
    It exists to validate source preservation, structure, and qualification flow.
    """
    manual = fixture["manual"]
    root = ET.Element(
        "syntheticTechnicalManual",
        attrib={
            "manualId": str(manual["manual_id"]),
            "revision": str(manual["revision"]),
        },
    )
    marking = ET.SubElement(root, "distributionMarking")
    marking.text = str(manual["distribution_marking"])
    title = ET.SubElement(root, "title")
    title.text = str(manual["title"])

    sections = ET.SubElement(root, "sections")
    for section in manual["sections"]:
        section_node = ET.SubElement(
            sections,
            "section",
            attrib={"id": str(section["section_id"]), "title": str(section["title"])},
        )
        for step in section["steps"]:
            step_node = ET.SubElement(section_node, "step", attrib={"id": str(step["step_id"])})
            step_node.text = str(step["text"])

    return ET.tostring(root, encoding="unicode")


def inspect_synthetic_projection(xml_text: str, fixture: dict[str, Any]) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    sections = root.findall("./sections/section")
    steps = root.findall("./sections/section/step")
    marking = root.findtext("distributionMarking")
    return {
        "section_count": len(sections),
        "step_count": len(steps),
        "marking_preserved": marking == fixture["manual"]["distribution_marking"],
        "manual_id_preserved": root.attrib.get("manualId") == fixture["manual"]["manual_id"],
    }


def qualify_synthetic_ietm(
    *,
    fixture: dict[str, Any],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    xml_text = project_synthetic_manual_to_xml(fixture)
    observed = inspect_synthetic_projection(xml_text, fixture)
    expected = fixture["expected"]
    passed = all(observed[key] == expected[key] for key in expected)

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-3001",
        requirement_id=requirement.requirement_delta_id,
        test_id="ietm_synthetic_projection_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest(
            {"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}
        ),
        configuration_digest=canonical_digest({"projector": "synthetic_xml_v1"}),
        inputs=[{"manual_id": fixture["manual"]["manual_id"]}],
        outputs=[{"xml_digest": canonical_digest({"xml": xml_text}), "observed": observed}],
        metrics=[{"name": key, "value": value, "expected": expected[key]} for key, value in observed.items()],
        uncertainty=[
            {
                "name": "standards_compliance",
                "state": "NOT_EVALUATED",
                "note": "No S1000D/MIL-standard validator has been applied",
            }
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=(
            "Synthetic XML projection preserved frozen structural/marking expectations"
            if passed
            else "Synthetic XML projection failed one or more frozen expectations"
        ),
        negative_evidence=[] if passed else [{"expected": expected, "observed": observed}],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence])
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["scope_note"] = (
        "Synthetic XML transformation evidence only; no S1000D, MIL-standard, Navy-viewer, or production conversion claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
