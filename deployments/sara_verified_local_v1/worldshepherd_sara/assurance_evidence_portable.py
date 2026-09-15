from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from .assurance_evidence_bundle import (
    AssuranceEvidenceBundle,
    verify_assurance_evidence_chain,
)


PORTABLE_ASSURANCE_SCHEMA = "WS-ASSURANCE-PORTABLE-V1"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class PortableAssurancePackage(BaseModel):
    schema: Literal[PORTABLE_ASSURANCE_SCHEMA] = PORTABLE_ASSURANCE_SCHEMA
    package_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    created_utc: str = Field(min_length=1)
    bundles: list[AssuranceEvidenceBundle] = Field(min_length=1)
    chain_digest: str = Field(pattern=_SHA256_PATTERN)
    package_digest: str = Field(pattern=_SHA256_PATTERN)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _chain_digest(bundles: list[AssuranceEvidenceBundle]) -> str:
    return _digest([bundle.manifest_digest for bundle in bundles])


def _package_payload(package: PortableAssurancePackage | dict[str, Any]) -> dict[str, Any]:
    if isinstance(package, PortableAssurancePackage):
        payload = package.model_dump(mode="json")
    else:
        payload = dict(package)
    payload.pop("package_digest", None)
    return payload


def build_portable_assurance_package(
    *,
    package_id: str,
    created_utc: str,
    bundles: list[AssuranceEvidenceBundle],
) -> PortableAssurancePackage:
    if not verify_assurance_evidence_chain(bundles):
        raise ValueError("cannot package an invalid assurance evidence chain")
    payload: dict[str, Any] = {
        "schema": PORTABLE_ASSURANCE_SCHEMA,
        "package_id": package_id,
        "created_utc": created_utc,
        "bundles": [bundle.model_dump(mode="json") for bundle in bundles],
        "chain_digest": _chain_digest(bundles),
    }
    payload["package_digest"] = _digest(payload)
    return PortableAssurancePackage.model_validate(payload)


def verify_portable_assurance_package(package: PortableAssurancePackage) -> bool:
    if not verify_assurance_evidence_chain(package.bundles):
        return False
    if package.chain_digest != _chain_digest(package.bundles):
        return False
    return package.package_digest == _digest(_package_payload(package))


def serialize_portable_assurance_package(package: PortableAssurancePackage) -> str:
    if not verify_portable_assurance_package(package):
        raise ValueError("portable assurance package failed verification")
    return _canonical_bytes(package.model_dump(mode="json")).decode("utf-8")


def load_portable_assurance_package(serialized: str) -> PortableAssurancePackage:
    package = PortableAssurancePackage.model_validate_json(serialized)
    if not verify_portable_assurance_package(package):
        raise ValueError("portable assurance package failed verification")
    return package
