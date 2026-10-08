from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable


class Decision(str, Enum):
    PROMOTE = "PROMOTE"
    HOLD = "HOLD"
    DENY = "DENY"
    REVIEW = "REVIEW"
    DEMOTE = "DEMOTE"


class ContradictionSeverity(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    MATERIAL = "MATERIAL"
    CRITICAL = "CRITICAL"


class ReproductionClass(str, Enum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"
    R5 = "R5"


class EnvironmentComparability(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    ACCEPTABLE_VARIATION = "ACCEPTABLE_VARIATION"
    MATERIAL_VARIATION = "MATERIAL_VARIATION"
    NONCOMPARABLE = "NONCOMPARABLE"


REQUIRED_AST_SECTIONS = (
    "identity",
    "authority",
    "inputs",
    "environment",
    "transformation",
    "observations",
    "verification",
    "provenance",
    "claims",
)


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes suitable for content hashing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


class EvidenceContractError(ValueError):
    pass


def validate_ast_record(record: dict[str, Any]) -> None:
    missing = [section for section in REQUIRED_AST_SECTIONS if section not in record]
    if missing:
        raise EvidenceContractError(f"missing required AST sections: {', '.join(missing)}")

    identity = record["identity"]
    for key in ("ast_id", "schema_version", "project_id", "artifact_id"):
        if not identity.get(key):
            raise EvidenceContractError(f"missing identity.{key}")

    authority = record["authority"]
    if not authority.get("actor") or not authority.get("role"):
        raise EvidenceContractError("authority actor and role are required")

    verification = record["verification"]
    if verification.get("result") not in {"pass", "fail", "indeterminate"}:
        raise EvidenceContractError("verification.result must be pass, fail, or indeterminate")

    claims = record["claims"]
    if "requested_scope" not in claims or "maximum_permitted_scope" not in claims:
        raise EvidenceContractError("claims requested_scope and maximum_permitted_scope are required")


def ast_root_digest(record: dict[str, Any]) -> str:
    validate_ast_record(record)
    signed_view = {section: record[section] for section in REQUIRED_AST_SECTIONS}
    return sha256_digest(signed_view)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise EvidenceContractError("timestamps must include an explicit timezone")
    return parsed.astimezone(timezone.utc)


def evidence_temporal_state(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
) -> str:
    """Return CURRENT, REVIEW_DUE, EXPIRED, or SUPERSEDED for evidence."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    lifecycle = record.get("lifecycle", {})
    if lifecycle.get("superseded_by"):
        return "SUPERSEDED"
    if lifecycle.get("expires_at") and now >= _parse_utc(lifecycle["expires_at"]):
        return "EXPIRED"
    if lifecycle.get("review_after") and now >= _parse_utc(lifecycle["review_after"]):
        return "REVIEW_DUE"
    return "CURRENT"


def compare_environments(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    *,
    material_keys: Iterable[str],
    noncomparable_keys: Iterable[str] = (),
) -> EnvironmentComparability:
    """Classify explicit environment deltas without hiding them in a score."""
    noncomparable = set(noncomparable_keys)
    material = set(material_keys)
    changed = {key for key in set(reference) | set(candidate) if reference.get(key) != candidate.get(key)}
    if changed & noncomparable:
        return EnvironmentComparability.NONCOMPARABLE
    if changed & material:
        return EnvironmentComparability.MATERIAL_VARIATION
    if changed:
        return EnvironmentComparability.ACCEPTABLE_VARIATION
    return EnvironmentComparability.EQUIVALENT


@dataclass(frozen=True)
class PromotionPolicy:
    required_sections: tuple[str, ...] = REQUIRED_AST_SECTIONS
    required_reproduction: ReproductionClass | None = None
    require_complete_measurements: bool = True
    require_provenance_integrity: bool = True
    require_environment: bool = True
    human_gate_required: bool = False


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    reasons: tuple[str, ...]
    permitted_claim_scope: int
    ast_digest: str


_REPRODUCTION_RANK = {
    ReproductionClass.R0: 0,
    ReproductionClass.R1: 1,
    ReproductionClass.R2: 2,
    ReproductionClass.R3: 3,
    ReproductionClass.R4: 4,
    ReproductionClass.R5: 5,
}


def _reproduction_satisfies(actual: str | None, required: ReproductionClass | None) -> bool:
    if required is None:
        return True
    if actual is None:
        return False
    try:
        actual_class = ReproductionClass(actual)
    except ValueError:
        return False
    return _REPRODUCTION_RANK[actual_class] >= _REPRODUCTION_RANK[required]


def evaluate_transition(record: dict[str, Any], policy: PromotionPolicy | None = None) -> Evaluation:
    policy = policy or PromotionPolicy()
    validate_ast_record(record)

    reasons: list[str] = []
    requested = int(record["claims"]["requested_scope"])
    maximum = int(record["claims"]["maximum_permitted_scope"])
    contradiction = ContradictionSeverity(record["verification"].get("contradiction_severity", "NONE"))

    if requested > maximum:
        reasons.append("CLAIM_EXCEEDS_EVIDENCE")

    if record["verification"]["result"] == "fail":
        reasons.append("VERIFICATION_FAILED")
    elif record["verification"]["result"] == "indeterminate":
        reasons.append("VERIFICATION_INDETERMINATE")

    if policy.require_provenance_integrity and not record["provenance"].get("integrity_ok", False):
        reasons.append("PROVENANCE_INCOMPLETE")

    if policy.require_environment and not record["environment"].get("captured", False):
        reasons.append("ENVIRONMENT_INCOMPLETE")

    if policy.require_complete_measurements and not record["observations"].get("complete", False):
        reasons.append("MEASUREMENTS_INCOMPLETE")

    if not record["authority"].get("authorized", False):
        reasons.append("UNAUTHORIZED")

    if policy.human_gate_required and not record["authority"].get("human_gate_approved", False):
        reasons.append("HUMAN_GATE_REQUIRED")

    if not _reproduction_satisfies(
        record["verification"].get("reproduction_class"),
        policy.required_reproduction,
    ):
        reasons.append("REPRODUCTION_LEVEL_INSUFFICIENT")

    temporal_state = evidence_temporal_state(record)
    if temporal_state == "EXPIRED":
        reasons.append("EVIDENCE_EXPIRED")
    elif temporal_state == "SUPERSEDED":
        reasons.append("EVIDENCE_SUPERSEDED")
    elif temporal_state == "REVIEW_DUE":
        reasons.append("EVIDENCE_REVIEW_DUE")

    if contradiction == ContradictionSeverity.CRITICAL:
        decision = Decision.DEMOTE
        reasons.append("CRITICAL_CONTRADICTION")
    elif contradiction == ContradictionSeverity.MATERIAL:
        decision = Decision.REVIEW
        reasons.append("MATERIAL_CONTRADICTION")
    elif "UNAUTHORIZED" in reasons or "CLAIM_EXCEEDS_EVIDENCE" in reasons or "VERIFICATION_FAILED" in reasons:
        decision = Decision.DENY
    elif reasons:
        decision = Decision.HOLD
    else:
        decision = Decision.PROMOTE

    return Evaluation(
        decision=decision,
        reasons=tuple(reasons),
        permitted_claim_scope=maximum,
        ast_digest=ast_root_digest(record),
    )


@dataclass
class ClaimNode:
    claim_id: str
    status: str = "ACTIVE"
    evidence_ids: set[str] = field(default_factory=set)
    parent_claims: set[str] = field(default_factory=set)


class ClaimGraph:
    """Small in-memory claim dependency DAG with recursive suspension."""

    def __init__(self) -> None:
        self._claims: dict[str, ClaimNode] = {}
        self._children: dict[str, set[str]] = {}

    def add_claim(
        self,
        claim_id: str,
        *,
        evidence_ids: Iterable[str] = (),
        parent_claims: Iterable[str] = (),
    ) -> None:
        parents = set(parent_claims)
        if claim_id in parents:
            raise EvidenceContractError("claim cannot depend on itself")
        if claim_id in self._claims:
            raise EvidenceContractError(f"claim already exists: {claim_id}")
        for parent in parents:
            if self._would_create_cycle(claim_id, parent):
                raise EvidenceContractError(
                    f"dependency would create a claim cycle: {claim_id} <- {parent}"
                )
        node = ClaimNode(claim_id, "ACTIVE", set(evidence_ids), parents)
        self._claims[claim_id] = node
        for parent in parents:
            self._children.setdefault(parent, set()).add(claim_id)

    def _would_create_cycle(self, claim_id: str, parent: str) -> bool:
        if parent == claim_id:
            return True
        stack = [parent]
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current == claim_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            node = self._claims.get(current)
            if node is not None:
                stack.extend(node.parent_claims)
        return False

    def status(self, claim_id: str) -> str:
        return self._claims[claim_id].status

    def suspend_for_evidence(self, evidence_id: str) -> set[str]:
        roots = {
            claim_id
            for claim_id, node in self._claims.items()
            if evidence_id in node.evidence_ids
        }
        return self._suspend_recursive(roots)

    def suspend_claim(self, claim_id: str) -> set[str]:
        return self._suspend_recursive({claim_id})

    def _suspend_recursive(self, roots: set[str]) -> set[str]:
        changed: set[str] = set()
        stack = list(roots)
        while stack:
            claim_id = stack.pop()
            node = self._claims.get(claim_id)
            if node is None or node.status == "SUSPENDED":
                continue
            node.status = "SUSPENDED"
            changed.add(claim_id)
            stack.extend(self._children.get(claim_id, ()))
        return changed


def confidence_vector(
    *,
    provenance_integrity: float,
    measurement_quality: float,
    reproducibility: float,
    independence: float,
    environmental_similarity: float,
    statistical_strength: float,
    external_support: float,
) -> dict[str, float]:
    values = {
        "provenance_integrity": provenance_integrity,
        "measurement_quality": measurement_quality,
        "reproducibility": reproducibility,
        "independence": independence,
        "environmental_similarity": environmental_similarity,
        "statistical_strength": statistical_strength,
        "external_support": external_support,
    }
    for name, value in values.items():
        if not 0.0 <= value <= 1.0:
            raise EvidenceContractError(f"{name} must be between 0 and 1")
    return values
