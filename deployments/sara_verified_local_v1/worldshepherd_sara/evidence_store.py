from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from .qualification import canonical_digest


class EvidenceIntegrityError(RuntimeError):
    pass


class EvidenceStore:
    """Small local hash-addressed evidence store for qualification bundles.

    The store provides local custody/integrity behavior only. It is not a
    government records system, WORM archive, legal chain-of-custody service, or
    accredited evidence repository.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)

    @staticmethod
    def _payload_digest(bundle: dict[str, Any]) -> str:
        payload = dict(bundle)
        payload.pop("bundle_digest", None)
        return canonical_digest(payload)

    @staticmethod
    def _digest_filename(digest: str) -> str:
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError("expected sha256:<64 lowercase hex> digest")
        hex_part = digest.split(":", 1)[1]
        if any(char not in "0123456789abcdef" for char in hex_part):
            raise ValueError("digest must be lowercase hexadecimal")
        return f"{hex_part}.json"

    def put_bundle(self, bundle: dict[str, Any]) -> str:
        expected = self._payload_digest(bundle)
        declared = bundle.get("bundle_digest")
        if declared != expected:
            raise EvidenceIntegrityError(
                f"bundle digest mismatch: declared={declared!r} expected={expected!r}"
            )

        target = self.root / self._digest_filename(expected)
        if target.exists():
            existing = self.get_bundle(expected)
            if existing != bundle:
                raise EvidenceIntegrityError("digest collision or inconsistent existing bundle")
            return expected

        encoded = (
            json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        temp = self.root / f".{target.name}.{secrets.token_hex(8)}.tmp"
        descriptor = os.open(
            temp,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, target)
            os.chmod(target, 0o600)
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)
        return expected

    def get_bundle(self, digest: str) -> dict[str, Any]:
        path = self.root / self._digest_filename(digest)
        if not path.exists():
            raise KeyError(digest)
        bundle = json.loads(path.read_text(encoding="utf-8"))
        actual = self._payload_digest(bundle)
        declared = bundle.get("bundle_digest")
        if actual != digest or declared != digest:
            raise EvidenceIntegrityError(
                f"stored bundle integrity failure: requested={digest} declared={declared} actual={actual}"
            )
        return bundle

    def verify_all(self) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for path in sorted(self.root.glob("*.json")):
            digest = f"sha256:{path.stem}"
            try:
                self.get_bundle(digest)
            except (EvidenceIntegrityError, json.JSONDecodeError, OSError, ValueError):
                results[digest] = False
            else:
                results[digest] = True
        return results
