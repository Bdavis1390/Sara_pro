from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

CONTEXT = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
BASE = "https://worldshepherd.dev/ws-cae/spdx"
PROFILE_BASE = "https://spdx.org/rdf/3.0.1/terms/Core/ProfileIdentifierType"
PROFILE_CONFORMANCE = [
    f"{PROFILE_BASE}/core",
    f"{PROFILE_BASE}/software",
    f"{PROFILE_BASE}/extension",
]


def _token(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:24]


def _properties(values: list[tuple[str, str]]) -> dict:
    return {
        "type": "extension_CdxPropertiesExtension",
        "extension_cdxProperty": [
            {
                "type": "extension_CdxPropertyEntry",
                "extension_cdxPropName": key,
                "extension_cdxPropValue": value,
            }
            for key, value in values
        ],
    }


def to_spdx(name: str, entries: list[dict], summary: dict[str, str]) -> dict:
    creation = "_:creationinfo"
    agent = f"{BASE}/agent/ws-cae"
    root_id = f"{BASE}/root/{_token(name)}"
    sbom_id = f"{BASE}/sbom/{_token(name)}"
    document_id = f"{BASE}/document/{_token(name)}"
    graph: list[dict] = [
        {
            "type": "CreationInfo",
            "@id": creation,
            "specVersion": "3.0.1",
            "createdBy": [agent],
            "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
        {"type": "Organization", "spdxId": agent, "creationInfo": creation, "name": "WS-CAE"},
        {
            "type": "software_Package",
            "spdxId": root_id,
            "creationInfo": creation,
            "name": name,
            "extension": [_properties(sorted((str(k), str(v)) for k, v in summary.items()))],
        },
    ]
    element_ids = [root_id]
    for index, entry in enumerate(entries):
        entry_name = str(entry.get("name", f"entry-{index}"))
        item_id = f"{BASE}/item/{_token(name + '|' + str(index) + '|' + entry_name)}"
        rel_id = f"{BASE}/relationship/{_token(root_id + '|' + item_id)}"
        element_ids.extend([item_id, rel_id])
        graph.append(
            {
                "type": "software_Package",
                "spdxId": item_id,
                "creationInfo": creation,
                "name": entry_name,
                "extension": [_properties(sorted((str(k), str(v)) for k, v in entry.items() if k != "name"))],
            }
        )
        graph.append(
            {
                "type": "Relationship",
                "spdxId": rel_id,
                "creationInfo": creation,
                "from": root_id,
                "relationshipType": "dependsOn",
                "to": [item_id],
            }
        )
    graph.extend(
        [
            {
                "type": "software_Sbom",
                "spdxId": sbom_id,
                "creationInfo": creation,
                "profileConformance": PROFILE_CONFORMANCE,
                "rootElement": [root_id],
                "element": element_ids,
                "software_sbomType": ["analyzed"],
            },
            {
                "type": "SpdxDocument",
                "spdxId": document_id,
                "creationInfo": creation,
                "profileConformance": PROFILE_CONFORMANCE,
                "rootElement": [sbom_id],
                "element": [agent, sbom_id, *element_ids],
            },
        ]
    )
    return {"@context": CONTEXT, "@graph": graph}
