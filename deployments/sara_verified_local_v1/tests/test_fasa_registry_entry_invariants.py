from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.fasa import CapabilityLevel, CapabilityRegistryEntry


def test_registry_entry_rejects_authorization_above_assessed_level():
    with pytest.raises(ValidationError, match="cannot exceed assessed_level"):
        CapabilityRegistryEntry(
            model_id="model-A",
            model_version="1.0",
            assessed_level=CapabilityLevel.F2,
            maximum_authorized_level=CapabilityLevel.F3,
            evaluation_id="EVAL-INVALID-001",
            evaluation_current=True,
        )


def test_registry_entry_accepts_authorization_at_or_below_assessed_level():
    equal = CapabilityRegistryEntry(
        model_id="model-A",
        model_version="1.0",
        assessed_level=CapabilityLevel.F4,
        maximum_authorized_level=CapabilityLevel.F4,
        evaluation_id="EVAL-VALID-001",
        evaluation_current=True,
    )
    below = CapabilityRegistryEntry(
        model_id="model-A",
        model_version="1.0",
        assessed_level=CapabilityLevel.F4,
        maximum_authorized_level=CapabilityLevel.F3,
        evaluation_id="EVAL-VALID-002",
        evaluation_current=True,
    )

    assert equal.maximum_authorized_level == CapabilityLevel.F4
    assert below.maximum_authorized_level == CapabilityLevel.F3
