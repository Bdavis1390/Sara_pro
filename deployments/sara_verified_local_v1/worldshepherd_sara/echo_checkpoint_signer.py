from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


SIGNER_ALGORITHM = "Ed25519"


class EchoCheckpointSignerError(RuntimeError):
    pass


@runtime_checkable
class EchoCheckpointSigner(Protocol):
    """Minimal non-exporting signing boundary used by ECHO checkpoints."""

    @property
    def algorithm(self) -> str: ...

    @property
    def key_id(self) -> str: ...

    def public_key_bytes(self) -> bytes: ...

    def sign(self, message: bytes) -> bytes: ...


@dataclass(frozen=True)
class LocalEd25519Signer:
    """Compatibility signer around local PEM-loaded key material.

    This signer preserves the current local software-key path. It is not a G7
    custody claim and must not be described as non-exportable hardware-backed
    signing.
    """

    private_key: Ed25519PrivateKey
    key_id: str

    @property
    def algorithm(self) -> str:
        return SIGNER_ALGORITHM

    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def sign(self, message: bytes) -> bytes:
        if not isinstance(message, bytes) or not message:
            raise EchoCheckpointSignerError(
                "checkpoint signer requires non-empty canonical bytes"
            )
        return self.private_key.sign(message)
