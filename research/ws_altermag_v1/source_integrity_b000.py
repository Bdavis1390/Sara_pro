from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile

from .schema import digest


PAIRS = [
    ("fig2b.csv", "fig2f.csv", "simulated_frequency_profiles"),
    ("fig2c.csv", "fig2g.csv", "selected_torque_traces"),
    ("fig2d.csv", "fig2h.csv", "selected_fft_spectra"),
]


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def _split_header_body(data: bytes) -> tuple[bytes, bytes]:
    lines = data.splitlines(keepends=True)
    if not lines:
        return b"", b""
    return lines[0], b"".join(lines[1:])


def audit_archive(zip_path: Path) -> dict:
    raw_zip = zip_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
        findings = []
        for left, right, role in PAIRS:
            lraw = zf.read(left)
            rraw = zf.read(right)
            lh, lb = _split_header_body(lraw)
            rh, rb = _split_header_body(rraw)
            findings.append(
                {
                    "left": left,
                    "right": right,
                    "role": role,
                    "left_full_sha256": _hash(lraw),
                    "right_full_sha256": _hash(rraw),
                    "left_header_sha256": _hash(lh),
                    "right_header_sha256": _hash(rh),
                    "left_body_sha256": _hash(lb),
                    "right_body_sha256": _hash(rb),
                    "full_equal": lraw == rraw,
                    "headers_equal": lh == rh,
                    "bodies_equal": lb == rb,
                }
            )

    ambiguous = [
        f for f in findings
        if f["bodies_equal"]
        and f["left"] != f["right"]
    ]

    record = {
        "program": "WS-ALTERMAG",
        "benchmark": "B000-DATA-INTEGRITY",
        "archive_sha256": _hash(raw_zip),
        "findings": findings,
        "duplicate_body_pair_count": len(ambiguous),
        "nodal_vs_antinodal_gate": "BLOCKED_SOURCE_DATA_AMBIGUITY" if ambiguous else "CLEAR",
        "pass": len(ambiguous) == 0,
        "claim_status": ["PROVEN INTERNALLY"],
        "claim_boundary": (
            "This audit reports byte-level relationships inside the pinned public source-data archive. "
            "It does not determine why duplicate bodies are present and does not attribute error to the authors."
        ),
        "next_gate": (
            "Use another unambiguous source-data path (for example the Fig. 3 tilted-plane dataset), "
            "or obtain clarification/corrected panel data before claiming automated Fig. 2 nodal-versus-antinodal reproduction."
        ),
    }
    record["evidence_digest"] = digest(record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_archive(args.zip)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
