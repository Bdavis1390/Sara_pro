from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.ocsf_full_projection import (
    OCSF_COMPILER_COMMIT,
    OCSF_SCHEMA_COMMIT,
    OCSF_TOOLKIT_COMMIT,
    OCSF_VERSION,
    build_full_ocsf_event,
)
from worldshepherd_sara.qualification import canonical_digest
from worldshepherd_sara.standards_interop import InteropCaseDefinition, build_interop_fixture


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "fixtures" / "standards_interop" / "corpus_v0_1.json"
LOCK_PATH = ROOT / "fixtures" / "standards_interop" / "corpus_v0_1.lock.json"
OUT_DIR = ROOT / "build" / "ocsf_projection_v0_3"


def main() -> None:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    source_digest = canonical_digest(corpus)
    if source_digest != lock["canonical_sha256"]:
        raise SystemExit("frozen source corpus digest does not match lock")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    case_ids: list[str] = []
    event_digests: dict[str, str] = {}
    source_event_digests: dict[str, str] = {}

    for raw_case in corpus["cases"]:
        case = InteropCaseDefinition.model_validate(raw_case)
        fixture = build_interop_fixture(case)
        event = build_full_ocsf_event(case)
        case_ids.append(case.case_id)
        source_event_digests[case.case_id] = fixture.correlation.ws_evidence_digest
        event_digests[case.case_id] = canonical_digest(event)
        path = OUT_DIR / f"{case.case_id}.event.json"
        path.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema": "WS-OCSF-CONFORMANCE-MANIFEST-V0.3",
        "source_corpus_path": str(CORPUS_PATH.relative_to(ROOT)),
        "source_corpus_digest": source_digest,
        "source_case_count": len(case_ids),
        "case_ids": case_ids,
        "source_event_digests": source_event_digests,
        "derived_event_digests": event_digests,
        "ocsf_schema_commit": OCSF_SCHEMA_COMMIT,
        "ocsf_schema_version": OCSF_VERSION,
        "ocsf_compiler_commit": OCSF_COMPILER_COMMIT,
        "ocsf_toolkit_commit": OCSF_TOOLKIT_COMMIT,
        "validation_status": "NOT_RUN",
        "claims_boundary": (
            "Derived synthetic event projections only. Successful validation would establish "
            "schema/toolkit conformance for these fixtures at the pinned revisions, not OCSF "
            "certification, endorsement, partner validation, production interoperability, or "
            "government acceptance."
        ),
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"built {len(case_ids)} OCSF event projections in {OUT_DIR}")


if __name__ == "__main__":
    main()
