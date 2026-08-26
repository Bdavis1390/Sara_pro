from __future__ import annotations

from worldshepherd_sara.common_services import AdapterManifest, ServiceManifest
from worldshepherd_sara.common_services_persistent import PersistentMissionEnclaveRegistry
from worldshepherd_sara.storage import DurableStore


def test_common_services_registry_survives_reopen_and_emits_audit(tmp_path):
    store = DurableStore(tmp_path / "data")
    registry = PersistentMissionEnclaveRegistry(store)
    v1 = ServiceManifest(
        service_id="echo-provenance",
        version="1.0.0",
        interface_version="1",
        software_digest="sha256:v1",
        sbom_digest="sha256:sbom1",
        required_authority="SSPADAWANZZ",
    )
    registry.register_service(v1)
    registry.register_adapter(
        AdapterManifest(
            adapter_id="synthetic-apnt",
            platform_family="synthetic",
            interface_version="1",
            software_digest="sha256:adapter",
        )
    )

    reopened = PersistentMissionEnclaveRegistry(DurableStore(tmp_path / "data"))
    assert reopened.service("echo-provenance").version == "1.0.0"
    assert reopened.adapter("synthetic-apnt").adapter_id == "synthetic-apnt"
    events = [item.get("event") for item in reopened.store.read_audit(20)]
    assert "common_service_registered" in events
    assert "common_adapter_registered" in events


def test_persistent_service_registry_supports_version_history_and_rollback(tmp_path):
    registry = PersistentMissionEnclaveRegistry(DurableStore(tmp_path / "data"))
    v1 = ServiceManifest(service_id="prime", version="1.0.0", interface_version="1", software_digest="sha256:v1", required_authority="CRE1AWS")
    v2 = v1.model_copy(update={"version":"1.1.0","software_digest":"sha256:v2"})
    registry.register_service(v1)
    registry.register_service(v2)
    assert registry.service("prime").version == "1.1.0"
    rolled_back = registry.rollback_service("prime")
    assert rolled_back.version == "1.0.0"
    assert registry.service("prime").version == "1.0.0"
