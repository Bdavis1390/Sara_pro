from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldshepherd_sara.models import RelayRequest


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_canonical_valid_relay_fixture_is_accepted_by_schema() -> None:
    request = RelayRequest.model_validate(load_fixture("runtime_relay_valid_v1.json"))

    assert request.target == "SSPADAWANZZ"
    assert request.action == "canonical_runtime_fixture_validation"
    assert request.payload["scope"] == "local"
    assert request.correlation_id == "fixture-valid-v1"


def test_canonical_invalid_relay_fixture_fails_closed() -> None:
    with pytest.raises(ValidationError):
        RelayRequest.model_validate(load_fixture("runtime_relay_invalid_v1.json"))
