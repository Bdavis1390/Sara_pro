"""Algorithm-agile digest sets for WS-CAE continuity manifests.

V1 content IDs remain SHA-256 for compatibility. Digest sets add parallel hash
identities so future policy can migrate without changing stable subject identity.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .continuity_manifest import ContinuityManifest, canonical_bytes

SUPPORTED = {
    "sha256": hashlib.sha256,
    "sha3-256": hashlib.sha3_256,
}


@dataclass(frozen=True)
class DigestSet:
    spec: str
    digests: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict:
        return {
            "spec": self.spec,
            "digests": {algorithm: digest for algorithm, digest in self.digests},
        }


def digest_set(
    manifest: ContinuityManifest,
    algorithms: tuple[str, ...] = ("sha256", "sha3-256"),
) -> DigestSet:
    if not algorithms:
        raise ValueError("at least one digest algorithm is required")
    if len(set(algorithms)) != len(algorithms):
        raise ValueError("digest algorithms must be unique")
    payload = canonical_bytes(manifest)
    values: list[tuple[str, str]] = []
    for algorithm in algorithms:
        constructor = SUPPORTED.get(algorithm)
        if constructor is None:
            raise ValueError(f"unsupported digest algorithm: {algorithm}")
        values.append((algorithm, constructor(payload).hexdigest()))
    values.sort(key=lambda item: item[0])
    return DigestSet("WS-CAE-CONTINUITY-DIGEST-SET-1", tuple(values))


def verify_digest_set(manifest: ContinuityManifest, value: DigestSet) -> bool:
    try:
        expected = digest_set(manifest, tuple(algorithm for algorithm, _ in value.digests))
    except ValueError:
        return False
    return expected == value


def select_digest(value: DigestSet, acceptable_algorithms: tuple[str, ...]) -> tuple[str, str] | None:
    available = dict(value.digests)
    for algorithm in acceptable_algorithms:
        digest = available.get(algorithm)
        if digest is not None:
            return algorithm, digest
    return None
