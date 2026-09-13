"""Read-only crypto-system dependency assessment for WS-CAE.

This module describes migration/readiness metadata only. It does not generate
keys, sign, access wallets, construct transactions, broadcast, or move assets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

COMPONENT_ROLES = {
    "CHAIN_AUTHORITY",
    "CONSENSUS_VALIDATOR",
    "ASSET_ISSUER_ADMIN",
    "BRIDGE_MESSAGING",
    "CUSTODY_SIGNING",
    "EXCHANGE_WITHDRAWAL",
    "WALLET_DEVICE",
    "RECOVERY",
    "ORACLE_ADMIN",
    "ROLLUP_PROVER",
    "PROTOCOL_ADMIN",
}

READINESS_ORDER = {
    "UNASSESSED": 0,
    "CLASSICAL_DEPENDENCY": 1,
    "CRYPTO_AGILE": 2,
    "PQ_PARTIAL": 3,
    "PQ_DEPLOYED": 4,
}


@dataclass(frozen=True)
class ComponentState:
    role: str
    name: str
    readiness_state: str
    critical: bool
    evidence_documented: bool


@dataclass(frozen=True)
class CryptoSystemPatch:
    asset: str
    components: tuple[ComponentState, ...]


@dataclass(frozen=True)
class CryptoSystemAssessment:
    valid: bool
    system_state: str
    weakest_readiness_state: str
    blocking_components: tuple[str, ...]
    issues: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_system(patch: CryptoSystemPatch) -> CryptoSystemAssessment:
    issues: list[str] = []
    if not patch.asset.strip():
        issues.append("asset must be non-empty")
    if not patch.components:
        issues.append("at least one component is required")

    critical = []
    for index, component in enumerate(patch.components):
        if component.role not in COMPONENT_ROLES:
            issues.append(f"component[{index}] role is not recognized")
        if not component.name.strip():
            issues.append(f"component[{index}] name must be non-empty")
        if component.readiness_state not in READINESS_ORDER:
            issues.append(f"component[{index}] readiness_state is not recognized")
        if not component.evidence_documented:
            issues.append(f"component[{index}] evidence is not documented")
        if component.critical:
            critical.append(component)

    if not critical:
        issues.append("at least one critical component is required")

    if issues or not critical:
        return CryptoSystemAssessment(
            False,
            "CRYPTO_SYSTEM_PATCH_INVALID",
            "UNASSESSED",
            tuple(),
            tuple(issues),
        )

    weakest_value = min(READINESS_ORDER[c.readiness_state] for c in critical)
    weakest = next(k for k, v in READINESS_ORDER.items() if v == weakest_value)
    blockers = tuple(
        f"{c.role}:{c.name}"
        for c in critical
        if READINESS_ORDER[c.readiness_state] == weakest_value
    )

    if weakest_value <= READINESS_ORDER["CLASSICAL_DEPENDENCY"]:
        state = "SYSTEM_MIGRATION_BLOCKED_BY_CRITICAL_DEPENDENCY"
    elif weakest_value < READINESS_ORDER["PQ_DEPLOYED"]:
        state = "SYSTEM_PARTIAL_PQ_READINESS"
    else:
        state = "ALL_DECLARED_CRITICAL_DEPENDENCIES_PQ_DEPLOYED"

    return CryptoSystemAssessment(True, state, weakest, blockers, tuple())
