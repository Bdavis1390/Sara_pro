#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    fmt = "unknown"
    trailing = b""
    structural_note = None

    if data.startswith(PNG_SIG):
        fmt = "png"
        marker = b"IEND"
        idx = data.rfind(marker)
        if idx >= 0:
            # IEND is type(4) + data(0) + CRC(4), with idx at type start.
            end = idx + 8
            trailing = data[end:] if end <= len(data) else b""
            structural_note = "PNG trailing bytes evaluated after IEND CRC"
    elif data.startswith(JPEG_SOI):
        fmt = "jpeg"
        idx = data.rfind(JPEG_EOI)
        if idx >= 0:
            trailing = data[idx + 2 :]
            structural_note = "JPEG trailing bytes evaluated after EOI"

    suspicious_tokens = []
    for token in (b"WS_FIXTURE_PAYLOAD", b"PK\x03\x04", b"BEGIN PGP", b"PRIVATE KEY"):
        if token in data:
            suspicious_tokens.append(token.decode("latin-1"))

    return {
        "schema": "WS-STEG-TRIAGE-RESULT-V1",
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "format": fmt,
        "trailing_bytes_count": len(trailing),
        "trailing_sha256": hashlib.sha256(trailing).hexdigest() if trailing else None,
        "suspicious_tokens": suspicious_tokens,
        "finding": bool(trailing or suspicious_tokens),
        "structural_note": structural_note,
        "boundary": "Digital file triage only; findings are hypotheses until reproducibly extracted and independently reviewed where material.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--output")
    args = ap.parse_args()

    results = [analyze(Path(p)) for p in args.files]
    text = json.dumps(results, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
