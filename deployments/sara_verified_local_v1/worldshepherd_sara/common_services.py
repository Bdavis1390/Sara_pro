from __future__ import annotations

from pydantic import BaseModel, Field


class ServiceManifest(BaseModel):
    service_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    interface_version: str = Field(min_length=1)
    software_digest: str = Field(min_length=1)
    sbom_digest: str | None = None
    required_authority: str = Field(min_length=1)
    health_endpoint: str | None = None


class AdapterManifest(BaseModel):
    adapter_id: str = Field(min_length=1)
    platform_family: str = Field(min_length=1)
    interface_version: str = Field(min_length=1)
    software_digest: str = Field(min_length=1)
    validation_state: str = "UNVALIDATED"


class MissionEnclaveRegistry:
    """In-memory contract registry for trusted-core prototype work only."""

    def __init__(self) -> None:
        self._services: dict[str, ServiceManifest] = {}
        self._adapters: dict[str, AdapterManifest] = {}
        self._service_history: dict[str, list[ServiceManifest]] = {}

    def register_service(self, manifest: ServiceManifest) -> None:
        current = self._services.get(manifest.service_id)
        if current is not None:
            self._service_history.setdefault(manifest.service_id, []).append(current)
        self._services[manifest.service_id] = manifest

    def register_adapter(self, manifest: AdapterManifest) -> None:
        self._adapters[manifest.adapter_id] = manifest

    def service(self, service_id: str) -> ServiceManifest:
        if service_id not in self._services:
            raise KeyError(service_id)
        return self._services[service_id]

    def adapter(self, adapter_id: str) -> AdapterManifest:
        if adapter_id not in self._adapters:
            raise KeyError(adapter_id)
        return self._adapters[adapter_id]

    def rollback_service(self, service_id: str) -> ServiceManifest:
        history = self._service_history.get(service_id, [])
        if not history:
            raise ValueError(f"no rollback state available for {service_id}")
        prior = history.pop()
        current = self._services[service_id]
        self._service_history.setdefault(service_id, []).append(current)
        self._services[service_id] = prior
        return prior

    def snapshot(self) -> dict[str, object]:
        return {
            "services": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self._services.items())
            },
            "adapters": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self._adapters.items())
            },
        }
