from __future__ import annotations

from typing import Any

from .common_services import AdapterManifest, ServiceManifest
from .models import AuditRecord
from .storage import DurableStore


_REGISTRY_KEY = "worldshepherd_common_services_v1"


class PersistentMissionEnclaveRegistry:
    """Durable Common Services/adapter registry using SARA's secured store.

    This provides local persistence and audit integration only. It is not a
    platform certification authority, software factory, or government registry.
    """

    def __init__(self, store: DurableStore) -> None:
        self.store = store

    def _state(self) -> dict[str, Any]:
        registry = self.store.get_registry()
        value = registry.get(_REGISTRY_KEY, {})
        if not isinstance(value, dict):
            raise ValueError("persistent common-services registry must be an object")
        return {
            "services": dict(value.get("services", {})),
            "adapters": dict(value.get("adapters", {})),
            "service_history": dict(value.get("service_history", {})),
        }

    def _write(self, state: dict[str, Any], *, event: str, payload: dict[str, Any]) -> None:
        self.store.patch_registry({_REGISTRY_KEY: state})
        self.store.append_audit(AuditRecord.create(event=event, actor="system", payload=payload))

    def register_service(self, manifest: ServiceManifest) -> None:
        state = self._state()
        service_id = manifest.service_id
        current = state["services"].get(service_id)
        if current is not None:
            state["service_history"].setdefault(service_id, []).append(current)
        state["services"][service_id] = manifest.model_dump(mode="json")
        self._write(
            state,
            event="common_service_registered",
            payload={"service_id": service_id, "version": manifest.version},
        )

    def register_adapter(self, manifest: AdapterManifest) -> None:
        state = self._state()
        state["adapters"][manifest.adapter_id] = manifest.model_dump(mode="json")
        self._write(
            state,
            event="common_adapter_registered",
            payload={"adapter_id": manifest.adapter_id, "platform_family": manifest.platform_family},
        )

    def service(self, service_id: str) -> ServiceManifest:
        state = self._state()
        if service_id not in state["services"]:
            raise KeyError(service_id)
        return ServiceManifest.model_validate(state["services"][service_id])

    def adapter(self, adapter_id: str) -> AdapterManifest:
        state = self._state()
        if adapter_id not in state["adapters"]:
            raise KeyError(adapter_id)
        return AdapterManifest.model_validate(state["adapters"][adapter_id])

    def rollback_service(self, service_id: str) -> ServiceManifest:
        state = self._state()
        history = state["service_history"].get(service_id, [])
        if not history:
            raise ValueError(f"no rollback state available for {service_id}")
        prior = history.pop()
        current = state["services"][service_id]
        history.append(current)
        state["service_history"][service_id] = history
        state["services"][service_id] = prior
        manifest = ServiceManifest.model_validate(prior)
        self._write(
            state,
            event="common_service_rolled_back",
            payload={"service_id": service_id, "version": manifest.version},
        )
        return manifest

    def snapshot(self) -> dict[str, Any]:
        return self._state()
