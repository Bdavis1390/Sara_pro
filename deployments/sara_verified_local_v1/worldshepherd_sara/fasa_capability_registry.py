from __future__ import annotations

from typing import Any

from .fasa import CapabilityRegistryEntry


FASA_CAPABILITY_REGISTRY_KEY = "FASA_CAPABILITY_REGISTRY"


class FASACapabilityRegistryError(ValueError):
    pass


def _capability_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(FASA_CAPABILITY_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise FASACapabilityRegistryError(
            f"{FASA_CAPABILITY_REGISTRY_KEY} must be a JSON object"
        )
    return dict(raw)


def authoritative_capability_entry(
    registry: dict[str, Any],
    *,
    model_id: str,
    model_version: str,
) -> CapabilityRegistryEntry:
    records = _capability_map(registry)
    versions = records.get(model_id)
    if not isinstance(versions, dict):
        raise FASACapabilityRegistryError(
            "candidate model identity is not present in the authoritative capability registry"
        )
    raw_entry = versions.get(model_version)
    if not isinstance(raw_entry, dict):
        raise FASACapabilityRegistryError(
            "candidate model version is not present in the authoritative capability registry"
        )
    try:
        entry = CapabilityRegistryEntry.model_validate(raw_entry)
    except ValueError as exc:
        raise FASACapabilityRegistryError(
            "authoritative capability registry entry is malformed"
        ) from exc
    if entry.model_id != model_id or entry.model_version != model_version:
        raise FASACapabilityRegistryError(
            "authoritative capability registry key does not match stored model identity/version"
        )
    return entry


def capability_registry_patch(
    registry: dict[str, Any],
    entry: CapabilityRegistryEntry,
    *,
    expected_evaluation_id: str | None = None,
) -> dict[str, Any]:
    """Return a protected-namespace patch with compare-and-swap replacement semantics.

    New model/version identities can be inserted directly. Replacing an existing
    identity requires the caller to name the evaluation_id currently in durable
    storage. A changed evaluation must receive a new evaluation_id; an evaluation
    identifier is therefore immutable once recorded.
    """

    records = _capability_map(registry)
    existing_versions = records.get(entry.model_id, {})
    if not isinstance(existing_versions, dict):
        raise FASACapabilityRegistryError(
            "authoritative capability registry model bucket is malformed"
        )
    versions = dict(existing_versions)
    existing_raw = versions.get(entry.model_version)
    serialized = entry.model_dump(mode="json")

    if existing_raw is not None:
        if not isinstance(existing_raw, dict):
            raise FASACapabilityRegistryError(
                "authoritative capability registry entry is malformed"
            )
        try:
            existing = CapabilityRegistryEntry.model_validate(existing_raw)
        except ValueError as exc:
            raise FASACapabilityRegistryError(
                "authoritative capability registry entry is malformed"
            ) from exc

        if existing.model_dump(mode="json") == serialized:
            return {FASA_CAPABILITY_REGISTRY_KEY: records}

        if expected_evaluation_id is None:
            raise FASACapabilityRegistryError(
                "replacing an authoritative capability entry requires expected_evaluation_id"
            )
        if existing.evaluation_id != expected_evaluation_id:
            raise FASACapabilityRegistryError(
                "authoritative capability entry changed since it was read"
            )
        if existing.evaluation_id == entry.evaluation_id:
            raise FASACapabilityRegistryError(
                "changed capability evaluation must use a new evaluation_id"
            )
    elif expected_evaluation_id is not None:
        raise FASACapabilityRegistryError(
            "expected_evaluation_id was supplied for a capability entry that does not exist"
        )

    versions[entry.model_version] = serialized
    records[entry.model_id] = versions
    return {FASA_CAPABILITY_REGISTRY_KEY: records}
