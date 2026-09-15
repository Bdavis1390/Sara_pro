#!/usr/bin/env python3
from __future__ import annotations

import binascii
import struct
import zlib
from pathlib import Path


def chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)


def png_1x1() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw_scanline = b"\x00\x00\x00\x00"
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_scanline)) + chunk(b"IEND", b"")


def main() -> int:
    out = Path(__file__).resolve().parent / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    clean = png_1x1()
    (out / "clean.png").write_bytes(clean)
    (out / "embedded.png").write_bytes(clean + b"WS_FIXTURE_PAYLOAD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
