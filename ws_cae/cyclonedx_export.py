"""CycloneDX 1.7 export for WS-CAE crypto-system dependency patches.

This bridge is read-only. It maps WS-CAE dependency metadata into a standard
CycloneDX BOM shape so existing security inventory tooling can ingest the
system graph. It does not generate keys, sign, access wallets, construct
transactions, broadcast, or move assets.
"""

from __future__ import annotations

import hashlib
import json
import uuid

from .crypto_system import CryptoSystemPatch, assess_system


def _safe_ref(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"urn:ws-cae:{digest}"


def _property(name: str, value: str) -> dict:
    return {"name": name, "value": value}


def export_cyclonedx(patch: CryptoSystemPatch) -> dict:
    assessment = assess_system(patch)
    asset_ref = _safe_ref(f"asset:{patch.asset}")
    components = []
    depends_on = []

    for component in patch.components:
        ref = _safe_ref(
            f"component:{patch.asset}:{component.role}:{component.name}:{component.readiness_state}"
        )
        depends_on.append(ref)
        components.append(
            {
                "type": "application",
                "bom-ref": ref,
                "name": component.name,
                "properties": [
                    _property("ws-cae:role", component.role),
                    _property("ws-cae:readiness-state", component.readiness_state),
                    _property("ws-cae:critical", str(component.critical).lower()),
                    _property(
                        "ws-cae:evidence-documented",
                        str(component.evidence_documented).lower(),
                    ),
                ],
            }
        )

    canonical = json.dumps(
        {
            "asset": patch.asset,
            "components": [
                {
                    "role": c.role,
                    "name": c.name,
                    "readiness_state": c.readiness_state,
                    "critical": c.critical,
                    "evidence_documented": c.evidence_documented,
                }
                for c in patch.components
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    serial = uuid.uuid5(uuid.NAMESPACE_URL, "urn:ws-cae:crypto-system:" + canonical)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": asset_ref,
                "name": patch.asset,
                "properties": [
                    _property("ws-cae:system-state", assessment.system_state),
                    _property(
                        "ws-cae:weakest-readiness-state",
                        assessment.weakest_readiness_state,
                    ),
                    _property("ws-cae:valid", str(assessment.valid).lower()),
                ],
            }
        },
        "components": components,
        "dependencies": [{"ref": asset_ref, "dependsOn": sorted(depends_on)}],
    }
