from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


RestrictionFieldKind = Literal["enum", "integer"]
EMPTY_CONTEXT_PROFILE_ID = "WS-RESTRICTION-CONTEXT-EMPTY-V1"
CHAT_ASSISTANT_PROFILE_ID = "WS-RESTRICTION-CONTEXT-CHAT-ASSISTANT-V1"


class RestrictionContextPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class MetadataRule:
    kind: RestrictionFieldKind
    allowed_values: frozenset[str] = frozenset()
    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True)
class RestrictionContextProfile:
    profile_id: str
    metadata_rules: dict[str, MetadataRule]
    allowed_summaries: frozenset[str]


_CLAIMS_STATES = frozenset(
    {
        "PROVEN_INTERNALLY",
        "IMPLEMENTED_IN_SOFTWARE",
        "SUPPORTED_BY_LITERATURE",
        "SIMULATED_ONLY",
        "HYPOTHESIS",
        "SPECULATIVE_EXTENSION",
        "REQUIRES_LAB_VALIDATION",
        "REQUIRES_PARTNER_VALIDATION",
        "REQUIRES_LEGAL_REVIEW",
        "NOT_CURRENTLY_CLAIMED",
    }
)

_CHAT_ASSISTANT_PROFILE = RestrictionContextProfile(
    profile_id=CHAT_ASSISTANT_PROFILE_ID,
    metadata_rules={
        "stage": MetadataRule(
            kind="enum",
            allowed_values=frozenset(
                {
                    "pre_generation_policy_check",
                    "post_generation_policy_check",
                    "connector_policy_check",
                }
            ),
        ),
        "claims_state": MetadataRule(
            kind="enum",
            allowed_values=_CLAIMS_STATES,
        ),
        "attempt": MetadataRule(
            kind="integer",
            minimum=1,
            maximum=1000,
        ),
    },
    allowed_summaries=frozenset(
        {"Output was restricted; only bounded provenance is retained."}
    ),
)

_PROFILES: dict[tuple[str, str], RestrictionContextProfile] = {
    ("CHAT_ASSISTANT", "POLICY_GATE"): _CHAT_ASSISTANT_PROFILE,
}


def _validate_rule(name: str, value: Any, rule: MetadataRule) -> Any:
    if rule.kind == "enum":
        if not isinstance(value, str) or value not in rule.allowed_values:
            raise RestrictionContextPolicyError(
                f"metadata field {name!r} is not allowed by the registered context profile"
            )
        return value

    if rule.kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise RestrictionContextPolicyError(
                f"metadata field {name!r} must be an integer"
            )
        if rule.minimum is not None and value < rule.minimum:
            raise RestrictionContextPolicyError(
                f"metadata field {name!r} is below the registered minimum"
            )
        if rule.maximum is not None and value > rule.maximum:
            raise RestrictionContextPolicyError(
                f"metadata field {name!r} exceeds the registered maximum"
            )
        return value

    raise RestrictionContextPolicyError(
        f"metadata field {name!r} has an unsupported validation rule"
    )


def validate_restriction_context(
    *,
    source_system: str,
    processor: str,
    metadata: dict[str, Any],
    safe_summary: str | None,
) -> tuple[dict[str, Any], str | None]:
    """Apply a positive schema to persisted restriction context.

    Unknown source/processor pairs are permitted only when they provide no metadata
    and no summary. Registered pairs may use only explicitly declared scalar fields
    and fixed server-controlled summary strings. The selected profile identifier is
    inserted into metadata so the restriction ID is bound to the validation policy.
    """
    if not isinstance(metadata, dict):
        raise RestrictionContextPolicyError("restriction metadata must be a JSON object")

    if "context_profile" in metadata:
        raise RestrictionContextPolicyError(
            "context_profile is system-managed and must not be supplied by callers"
        )

    profile = _PROFILES.get((source_system, processor))
    if profile is None:
        if metadata:
            raise RestrictionContextPolicyError(
                "unregistered restriction source/processor pairs may not persist metadata"
            )
        if safe_summary is not None:
            raise RestrictionContextPolicyError(
                "unregistered restriction source/processor pairs may not persist a summary"
            )
        return {"context_profile": EMPTY_CONTEXT_PROFILE_ID}, None

    unknown_fields = sorted(set(metadata) - set(profile.metadata_rules))
    if unknown_fields:
        raise RestrictionContextPolicyError(
            "restriction metadata contains fields outside the registered context profile"
        )

    validated = {
        name: _validate_rule(name, value, profile.metadata_rules[name])
        for name, value in metadata.items()
    }
    validated["context_profile"] = profile.profile_id

    if safe_summary is not None and safe_summary not in profile.allowed_summaries:
        raise RestrictionContextPolicyError(
            "safe_summary is not an approved template for the registered context profile"
        )

    return validated, safe_summary


def registered_context_profile_ids() -> tuple[str, ...]:
    return tuple(sorted(profile.profile_id for profile in _PROFILES.values()))
