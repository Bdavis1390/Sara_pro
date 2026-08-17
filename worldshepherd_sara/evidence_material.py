from __future__ import annotations

import math
from typing import Any, Dict

from worldshepherd_sara.evidence_contract import (
    EVIDENCE_CLASSES,
    EvidenceValidationError,
    REVIEW_STATES,
)

COMPOSITION_BASES = {"WT_PERCENT", "AT_PERCENT", "MASS_FRACTION", "DECLARED_OTHER"}
BATCH_ROLES = {"FEEDSTOCK", "DEPOSIT", "COUPON", "COMPONENT", "REFERENCE"}


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceValidationError(f"{field} must be a non-empty string")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceValidationError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceValidationError(f"{field} must be finite")
    return result


def _evidence_class(value: Any, field: str) -> str:
    text = _string(value, field)
    if text not in EVIDENCE_CLASSES:
        raise EvidenceValidationError(
            f"{field} must be one of: {', '.join(sorted(EVIDENCE_CLASSES))}"
        )
    return text


def validate_material_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise EvidenceValidationError("material record must be a JSON object")

    required = {
        "material_batch_id",
        "material_system",
        "batch_role",
        "composition",
        "feedstock_ids",
        "process_history",
        "microstructure_observations",
        "properties",
        "component_links",
        "review_state",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise EvidenceValidationError(
            f"material record missing required fields: {', '.join(missing)}"
        )

    _string(payload["material_batch_id"], "material_batch_id")
    _string(payload["material_system"], "material_system")
    if payload["batch_role"] not in BATCH_ROLES:
        raise EvidenceValidationError(
            "batch_role must be one of: " + ", ".join(sorted(BATCH_ROLES))
        )
    if payload["review_state"] not in REVIEW_STATES:
        raise EvidenceValidationError(
            "review_state must be one of: " + ", ".join(sorted(REVIEW_STATES))
        )

    composition = payload["composition"]
    if not isinstance(composition, dict):
        raise EvidenceValidationError("composition must be a JSON object")
    basis = composition.get("basis")
    if basis not in COMPOSITION_BASES:
        raise EvidenceValidationError(
            "composition.basis must be one of: " + ", ".join(sorted(COMPOSITION_BASES))
        )
    constituents = composition.get("constituents")
    if not isinstance(constituents, list) or not constituents:
        raise EvidenceValidationError("composition.constituents must be a non-empty list")
    species: list[str] = []
    values: list[float] = []
    for index, constituent in enumerate(constituents):
        if not isinstance(constituent, dict):
            raise EvidenceValidationError(
                f"composition.constituents[{index}] must be a JSON object"
            )
        species.append(
            _string(constituent.get("species"), f"composition.constituents[{index}].species")
        )
        value = _number(
            constituent.get("fraction"), f"composition.constituents[{index}].fraction"
        )
        if value < 0:
            raise EvidenceValidationError("composition constituent fractions must be non-negative")
        values.append(value)
    if len(species) != len(set(species)):
        raise EvidenceValidationError("composition constituent species must be unique")
    if basis in {"WT_PERCENT", "AT_PERCENT"} and abs(sum(values) - 100.0) > 1e-6:
        raise EvidenceValidationError("percentage composition fractions must sum to 100")
    if basis == "MASS_FRACTION" and abs(sum(values) - 1.0) > 1e-9:
        raise EvidenceValidationError("mass-fraction composition must sum to 1")

    feedstock_ids = payload["feedstock_ids"]
    if not isinstance(feedstock_ids, list) or any(
        not isinstance(item, str) or not item for item in feedstock_ids
    ):
        raise EvidenceValidationError("feedstock_ids must be a list of non-empty strings")
    if len(feedstock_ids) != len(set(feedstock_ids)):
        raise EvidenceValidationError("feedstock_ids must not contain duplicates")

    process_history = payload["process_history"]
    if not isinstance(process_history, list):
        raise EvidenceValidationError("process_history must be a list")
    step_ids: list[str] = []
    for index, step in enumerate(process_history):
        if not isinstance(step, dict):
            raise EvidenceValidationError(f"process_history[{index}] must be a JSON object")
        step_ids.append(_string(step.get("step_id"), f"process_history[{index}].step_id"))
        _string(step.get("process_type"), f"process_history[{index}].process_type")
        if not isinstance(step.get("parameters"), dict):
            raise EvidenceValidationError(f"process_history[{index}].parameters must be an object")
        if "configuration_digest" in step:
            _string(
                step["configuration_digest"],
                f"process_history[{index}].configuration_digest",
            )
    if len(step_ids) != len(set(step_ids)):
        raise EvidenceValidationError("process_history step_id values must be unique")

    observations = payload["microstructure_observations"]
    if not isinstance(observations, list):
        raise EvidenceValidationError("microstructure_observations must be a list")
    observation_ids: list[str] = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise EvidenceValidationError(
                f"microstructure_observations[{index}] must be an object"
            )
        observation_ids.append(
            _string(
                observation.get("observation_id"),
                f"microstructure_observations[{index}].observation_id",
            )
        )
        _string(observation.get("method"), f"microstructure_observations[{index}].method")
        _evidence_class(
            observation.get("evidence_class"),
            f"microstructure_observations[{index}].evidence_class",
        )
        _string(observation.get("result"), f"microstructure_observations[{index}].result")
        sources = observation.get("source_record_ids", [])
        if not isinstance(sources, list) or any(not isinstance(item, str) or not item for item in sources):
            raise EvidenceValidationError(
                f"microstructure_observations[{index}].source_record_ids must be a string list"
            )
    if len(observation_ids) != len(set(observation_ids)):
        raise EvidenceValidationError("microstructure observation IDs must be unique")

    properties = payload["properties"]
    if not isinstance(properties, list):
        raise EvidenceValidationError("properties must be a list")
    property_ids: list[str] = []
    for index, prop in enumerate(properties):
        if not isinstance(prop, dict):
            raise EvidenceValidationError(f"properties[{index}] must be a JSON object")
        property_ids.append(_string(prop.get("property_id"), f"properties[{index}].property_id"))
        _string(prop.get("name"), f"properties[{index}].name")
        _string(prop.get("units"), f"properties[{index}].units")
        _number(prop.get("value"), f"properties[{index}].value")
        evidence = _evidence_class(prop.get("evidence_class"), f"properties[{index}].evidence_class")
        conditions = prop.get("conditions", {})
        if not isinstance(conditions, dict):
            raise EvidenceValidationError(f"properties[{index}].conditions must be an object")
        sources = prop.get("source_record_ids", [])
        if not isinstance(sources, list) or any(not isinstance(item, str) or not item for item in sources):
            raise EvidenceValidationError(
                f"properties[{index}].source_record_ids must be a string list"
            )
        if evidence == "MEASURED":
            if not sources:
                raise EvidenceValidationError(
                    f"properties[{index}] MEASURED property requires source_record_ids"
                )
            _string(prop.get("uncertainty_reference"), f"properties[{index}].uncertainty_reference")
    if len(property_ids) != len(set(property_ids)):
        raise EvidenceValidationError("property_id values must be unique")

    links = payload["component_links"]
    if not isinstance(links, list):
        raise EvidenceValidationError("component_links must be a list")
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            raise EvidenceValidationError(f"component_links[{index}] must be an object")
        _string(link.get("component_id"), f"component_links[{index}].component_id")
        _string(link.get("role"), f"component_links[{index}].role")

    return payload
