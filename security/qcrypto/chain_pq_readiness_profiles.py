"""Source-backed cryptocurrency post-quantum readiness profiles.

These profiles translate public, dated primary-source evidence into conservative
migration-readiness observations for selected cryptocurrency networks.  They are
not protocol conformance tests and they do not authorize transactions, keys,
wallet operations, or production migration.

Unknown evidence stays UNKNOWN.  A strong result in one layer never substitutes
for unresolved or classical dependencies elsewhere.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum


EVIDENCE_AS_OF = "2026-09-15"


class ProfileLayer(StrEnum):
    ACCOUNTS = "ACCOUNTS"
    CONSENSUS = "CONSENSUS"
    COMMITMENTS_ZK = "COMMITMENTS_ZK"
    BRIDGES_CUSTODY_ADMIN = "BRIDGES_CUSTODY_ADMIN"
    TOOLING_INTEROP = "TOOLING_INTEROP"
    RECOVERY = "RECOVERY"


class ObservedReadiness(IntEnum):
    UNKNOWN = -1
    CLASSICAL = 0
    HYBRID = 1
    PQ_CAPABLE = 2
    PQ_REQUIRED = 3


@dataclass(frozen=True)
class LayerObservation:
    layer: ProfileLayer
    readiness: ObservedReadiness
    statement: str
    source_urls: tuple[str, ...]


@dataclass(frozen=True)
class ChainProfile:
    chain_id: str
    evidence_as_of: str
    observations: tuple[LayerObservation, ...]
    source_class: str = "PUBLIC_PRIMARY_SOURCE_PROFILE"
    live_value_authorized: bool = False
    execution_authority: bool = False


@dataclass(frozen=True)
class ChainProfileDecision:
    chain_id: str
    verdict: str
    known_blocking_layers: tuple[str, ...]
    unknown_layers: tuple[str, ...]
    hybrid_layers: tuple[str, ...]
    pq_capable_layers: tuple[str, ...]
    migration_target_reached: bool
    whole_chain_pq_security_established: bool = False
    production_deployment_established: bool = False
    live_value_authorized: bool = False
    execution_authority: bool = False
    claim_boundary: str = (
        "Public-source migration-readiness profile only. Layer labels describe the "
        "cited scope as of the evidence date and do not establish whole-chain PQ "
        "security, protocol conformance, production migration, or third-party validation."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in (
            "known_blocking_layers",
            "unknown_layers",
            "hybrid_layers",
            "pq_capable_layers",
        ):
            data[key] = list(data[key])
        return data


BTC_BIP360 = "https://github.com/bitcoin/bips/blob/master/bip-0360.mediawiki"
BTC_BIP361 = "https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki"
ETH_PQ = "https://ethereum.org/roadmap/security/quantum-resistance/"
ETH_PQ_TEAM = "https://pq.ethereum.org/"
ALGO_PQ = "https://algorand.co/technology/post-quantum"
ALGO_PQ_ACCOUNT = "https://dev.algorand.co/concepts/accounts/post-quantum/"
ALGO_V5 = "https://algorand.co/blog/algorand-v5.0.0-has-arrived-heres-how-to-upgrade"


BITCOIN = ChainProfile(
    chain_id="BITCOIN",
    evidence_as_of=EVIDENCE_AS_OF,
    observations=(
        LayerObservation(
            ProfileLayer.ACCOUNTS,
            ObservedReadiness.CLASSICAL,
            "Legacy Bitcoin spend authorization remains quantum-vulnerable; BIP-360 and BIP-361 are Draft, and BIP-360 explicitly says short-exposure protection may require future post-quantum signatures.",
            (BTC_BIP360, BTC_BIP361),
        ),
        LayerObservation(
            ProfileLayer.CONSENSUS,
            ObservedReadiness.UNKNOWN,
            "Proof-of-work consensus does not map directly to validator-signature migration; consensus acceptance of proposed PQ output/signature changes is not established by the cited Draft BIPs.",
            (BTC_BIP360, BTC_BIP361),
        ),
        LayerObservation(
            ProfileLayer.COMMITMENTS_ZK,
            ObservedReadiness.UNKNOWN,
            "No complete commitments/ZK migration assessment is established by the cited BIP evidence.",
            (BTC_BIP360,),
        ),
        LayerObservation(
            ProfileLayer.BRIDGES_CUSTODY_ADMIN,
            ObservedReadiness.UNKNOWN,
            "Bridge, exchange, custody, and administrative authority readiness is ecosystem-specific and not established by these protocol proposals.",
            (BTC_BIP361,),
        ),
        LayerObservation(
            ProfileLayer.TOOLING_INTEROP,
            ObservedReadiness.HYBRID,
            "BIP-360 includes reference/test-vector work and BIP-361 defines a migration concept, but both remain Draft rather than deployed network policy.",
            (BTC_BIP360, BTC_BIP361),
        ),
        LayerObservation(
            ProfileLayer.RECOVERY,
            ObservedReadiness.UNKNOWN,
            "BIP-361 discusses legacy-sunset and vulnerable-output migration choices, but a universally deployed recovery path is not established.",
            (BTC_BIP361,),
        ),
    ),
)


ETHEREUM = ChainProfile(
    chain_id="ETHEREUM",
    evidence_as_of=EVIDENCE_AS_OF,
    observations=(
        LayerObservation(
            ProfileLayer.ACCOUNTS,
            ObservedReadiness.CLASSICAL,
            "Execution-layer externally owned accounts still depend on ECDSA; Ethereum plans signature agility/account abstraction as part of the PQ migration.",
            (ETH_PQ, ETH_PQ_TEAM),
        ),
        LayerObservation(
            ProfileLayer.CONSENSUS,
            ObservedReadiness.CLASSICAL,
            "Consensus still uses BLS signatures; leanXMSS and leanVM are active migration work rather than completed mainnet replacement.",
            (ETH_PQ, ETH_PQ_TEAM),
        ),
        LayerObservation(
            ProfileLayer.COMMITMENTS_ZK,
            ObservedReadiness.CLASSICAL,
            "Ethereum identifies KZG commitments and pairing-based ZK systems as quantum-vulnerable dependencies that require migration.",
            (ETH_PQ,),
        ),
        LayerObservation(
            ProfileLayer.BRIDGES_CUSTODY_ADMIN,
            ObservedReadiness.UNKNOWN,
            "The cited protocol roadmap does not establish PQ readiness for every bridge, custody system, upgrade authority, or application administrator.",
            (ETH_PQ_TEAM,),
        ),
        LayerObservation(
            ProfileLayer.TOOLING_INTEROP,
            ObservedReadiness.HYBRID,
            "Weekly post-quantum interop devnets and open-source leanEthereum components demonstrate active interoperability work, not completed ecosystem migration.",
            (ETH_PQ, ETH_PQ_TEAM),
        ),
        LayerObservation(
            ProfileLayer.RECOVERY,
            ObservedReadiness.UNKNOWN,
            "Dormant-account handling and broad user migration remain open governance/ecosystem questions in the cited roadmap.",
            (ETH_PQ,),
        ),
    ),
)


ALGORAND = ChainProfile(
    chain_id="ALGORAND",
    evidence_as_of=EVIDENCE_AS_OF,
    observations=(
        LayerObservation(
            ProfileLayer.ACCOUNTS,
            ObservedReadiness.PQ_CAPABLE,
            "Native Falcon-1024 accounts are live on Mainnet and can authorize transactions with post-quantum signatures.",
            (ALGO_PQ, ALGO_PQ_ACCOUNT, ALGO_V5),
        ),
        LayerObservation(
            ProfileLayer.CONSENSUS,
            ObservedReadiness.CLASSICAL,
            "Algorand states that consensus participation still relies on classical Ed25519-based key/signature operations and that PQ consensus is the remaining major protocol piece.",
            (ALGO_PQ,),
        ),
        LayerObservation(
            ProfileLayer.COMMITMENTS_ZK,
            ObservedReadiness.UNKNOWN,
            "Falcon State Proofs protect historical attestations, but this profile does not generalize that capability into a complete commitments/ZK-layer PQ claim.",
            (ALGO_PQ,),
        ),
        LayerObservation(
            ProfileLayer.BRIDGES_CUSTODY_ADMIN,
            ObservedReadiness.UNKNOWN,
            "The roadmap discusses future PQ multisig and institutional custody work; broad deployed authority migration is not established by the cited evidence.",
            (ALGO_PQ,),
        ),
        LayerObservation(
            ProfileLayer.TOOLING_INTEROP,
            ObservedReadiness.HYBRID,
            "Native Falcon accounts have SDK, AlgoKit, and Pera support, while the developer documentation warns that broader wallets, dApps, and tooling may not yet support PQ signing.",
            (ALGO_PQ, ALGO_PQ_ACCOUNT),
        ),
        LayerObservation(
            ProfileLayer.RECOVERY,
            ObservedReadiness.HYBRID,
            "Existing accounts can rekey authorization to Falcon, but account close-out/re-funding and ecosystem-support caveats prevent treating migration/recovery as universally complete.",
            (ALGO_PQ_ACCOUNT,),
        ),
    ),
)


PROFILES = {
    profile.chain_id: profile
    for profile in (BITCOIN, ETHEREUM, ALGORAND)
}


def assess_chain_profile(profile: ChainProfile) -> ChainProfileDecision:
    """Classify known blockers and evidence gaps without upgrading unknown evidence."""

    observations = {item.layer: item for item in profile.observations}
    expected = set(ProfileLayer)
    if set(observations) != expected:
        missing = tuple(sorted(layer.value for layer in expected - set(observations)))
        return ChainProfileDecision(
            chain_id=profile.chain_id,
            verdict="PROFILE_SCHEMA_INCOMPLETE",
            known_blocking_layers=(),
            unknown_layers=missing,
            hybrid_layers=(),
            pq_capable_layers=(),
            migration_target_reached=False,
        )

    classical = tuple(sorted(item.layer.value for item in profile.observations if item.readiness is ObservedReadiness.CLASSICAL))
    unknown = tuple(sorted(item.layer.value for item in profile.observations if item.readiness is ObservedReadiness.UNKNOWN))
    hybrid = tuple(sorted(item.layer.value for item in profile.observations if item.readiness is ObservedReadiness.HYBRID))
    pq_capable = tuple(sorted(item.layer.value for item in profile.observations if item.readiness >= ObservedReadiness.PQ_CAPABLE))

    if unknown:
        verdict = "INCOMPLETE_EVIDENCE_WITH_KNOWN_BLOCKERS" if classical else "INCOMPLETE_EVIDENCE"
        reached = False
    elif classical:
        verdict = "BLOCKED_BY_CLASSICAL_LAYER"
        reached = False
    elif hybrid:
        verdict = "HYBRID_MIGRATION_READY"
        reached = False
    else:
        verdict = "PQ_MIGRATION_READY"
        reached = True

    return ChainProfileDecision(
        chain_id=profile.chain_id,
        verdict=verdict,
        known_blocking_layers=classical,
        unknown_layers=unknown,
        hybrid_layers=hybrid,
        pq_capable_layers=pq_capable,
        migration_target_reached=reached,
    )
