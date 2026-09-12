from __future__ import annotations

import argparse
import json
from pathlib import Path

from .independent_review_verify import (
    MAX_SERIALIZED_REVIEW_BUNDLE_BYTES,
    IndependentReviewVerificationResult,
    build_independent_review_input_error_result,
    verify_serialized_independent_review_export,
)


EXIT_VERIFIED = 0
EXIT_VERIFICATION_FAILED = 1
EXIT_INPUT_READ_ERROR = 2


def _render_result(result: IndependentReviewVerificationResult) -> str:
    """Render one deterministic machine-readable verification result."""

    return json.dumps(
        result.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def _read_bounded(path: Path) -> bytes:
    """Read at most the verifier limit plus one byte from a saved bundle."""

    with path.open("rb") as handle:
        return handle.read(MAX_SERIALIZED_REVIEW_BUNDLE_BYTES + 1)


def main(argv: list[str] | None = None) -> int:
    """Verify one saved reviewer bundle and emit JSON to stdout only."""

    parser = argparse.ArgumentParser(
        prog="worldshepherd-independent-review-verify",
        description=(
            "Offline verification of a serialized Worldshepherd independent-review "
            "export bundle. PASS proves only the local evidence-reproduction checks."
        ),
    )
    parser.add_argument(
        "bundle",
        help="path to a saved WS-INDEPENDENT-REVIEW-EXPORT-BUNDLE-V1 JSON file",
    )
    args = parser.parse_args(argv)
    path = Path(args.bundle)

    try:
        serialized = _read_bounded(path)
    except OSError as exc:
        result = build_independent_review_input_error_result(
            f"unable to read reviewer bundle {path}: {exc}"
        )
        print(_render_result(result))
        return EXIT_INPUT_READ_ERROR

    result = verify_serialized_independent_review_export(serialized)
    print(_render_result(result))
    if result.status == "PASS":
        return EXIT_VERIFIED
    return EXIT_VERIFICATION_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
