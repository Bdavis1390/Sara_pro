from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "security/qcrypto/publication_manifest_2026-09-14.json"


def fail(message: str) -> None:
    raise SystemExit(f"QCRYPTO publication gate: FAIL: {message}")


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema") != "WS-QCRYPTO-PUBLICATION-MANIFEST-V1":
        fail("unsupported publication manifest schema")
    if manifest.get("publication_class") != "PUBLIC_TECHNICAL_WHITE_PAGE_NON_CONFIDENTIAL":
        fail("publication class is not public/non-confidential")
    if manifest.get("publication_state") != "POSTABLE_CANDIDATE":
        fail("publication state must remain POSTABLE_CANDIDATE until CI passes")
    if manifest.get("claims_state") != "PROVEN_INTERNALLY_BOUNDED_SOFTWARE_BEHAVIOR":
        fail("claims state exceeds or differs from bounded internal proof")

    anchor = manifest.get("validated_implementation_anchor")
    if not isinstance(anchor, str) or not re.fullmatch(r"[0-9a-f]{40}", anchor):
        fail("validated implementation anchor is not a full commit SHA")

    digest = manifest.get("bridge_artifact_digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        fail("bridge artifact digest is not a SHA-256 digest")

    document_path = ROOT / manifest["document"]
    if not document_path.is_file():
        fail("white-page document is missing")
    text = document_path.read_text(encoding="utf-8")

    required_literals = [
        "PUBLIC TECHNICAL WHITE PAGE / NON-CONFIDENTIAL",
        "POSTABLE CANDIDATE",
        "PROVEN INTERNALLY",
        anchor,
        digest,
        "decision_digest",
        "audit_instance_id",
        "ECHO SENTINEL LINK",
        "PRIME SENTINEL",
        "SARA",
        "OVERWATCH",
        "four explicit `MATCHED` records",
        "zero `SARA_ONLY`",
        "zero `PAYLOAD_MISMATCH`",
        "Ed25519",
        manifest["safety_boundary"],
    ]
    for literal in required_literals:
        if literal not in text:
            fail(f"required publication evidence phrase missing: {literal}")

    for nonclaim in manifest.get("required_nonclaims", []):
        if nonclaim.lower() not in text.lower():
            fail(f"required non-claim missing: {nonclaim}")

    prohibited_unbounded_claims = [
        r"\bquantum[- ]safe\b",
        r"\bquantum[- ]secure\b",
        r"\bproduction[- ]ready\b",
        r"\bfederally compliant\b",
        r"\bgovernment[- ]validated\b",
        r"\bpartner[- ]validated\b",
    ]
    lower = text.lower()
    for pattern in prohibited_unbounded_claims:
        if re.search(pattern, lower):
            fail(f"unbounded public claim present: {pattern}")

    words = re.findall(r"\b\w+[\w'-]*\b", text)
    if len(words) > 1700:
        fail(f"white page is too long for posting ({len(words)} words)")

    check = subprocess.run(
        ["git", "cat-file", "-e", f"{anchor}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode != 0:
        fail("validated implementation anchor is not present in repository history")

    print(
        json.dumps(
            {
                "schema": "WS-QCRYPTO-PUBLICATION-GATE-RESULT-V1",
                "status": "PASS",
                "posting_status": "GO",
                "validated_implementation_anchor": anchor,
                "bridge_artifact_digest": digest,
                "document": manifest["document"],
                "word_count": len(words),
                "claims_state": manifest["claims_state"],
                "publication_class": manifest["publication_class"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
