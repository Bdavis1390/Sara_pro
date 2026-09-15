from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.rmabm_external_bundle import (
    SAFE_RELATIVE_PATHS,
    build_external_evidence_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic review-required manifest for allowlisted W-RMABM "
            "unclassified/non-confidential candidate artifacts. This tool does not transmit files."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    args = parser.parse_args()

    manifest = build_external_evidence_manifest(
        repository_root=args.repo_root,
        relative_paths=SAFE_RELATIVE_PATHS,
    )
    print(json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
