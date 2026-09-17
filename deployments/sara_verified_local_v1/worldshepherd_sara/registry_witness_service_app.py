from __future__ import annotations

from .registry_witness_service import (
    RegistryWitnessService,
    create_registry_witness_app,
)


service = RegistryWitnessService.from_environment()
app = create_registry_witness_app(service)
