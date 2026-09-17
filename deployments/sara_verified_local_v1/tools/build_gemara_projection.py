from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.gemara_full_projection import build_full_gemara_documents
from worldshepherd_sara.standards_interop import InteropCaseDefinition

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "fixtures" / "standards_interop" / "corpus_v0_1.json"
OUTPUT = ROOT / "build" / "gemara_projection_v0_2"


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    raw = json.loads(CORPUS.read_text(encoding="utf-8"))
    cases = [InteropCaseDefinition.model_validate(item) for item in raw["cases"]]
    count = 0
    for case in cases:
        docs = build_full_gemara_documents(case)
        for kind, doc in docs.items():
            path = OUTPUT / f"{case.case_id.lower()}-{kind}.json"
            path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            count += 1
    manifest = {
        "schema": "WS-GEMARA-FULL-PROJECTION-MANIFEST-V0.2",
        "case_count": len(cases),
        "document_count": count,
        "external_validation_status": "PENDING_CI",
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
