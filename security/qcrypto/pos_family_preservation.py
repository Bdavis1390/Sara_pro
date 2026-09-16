"""WS-QPOS-FAMILY bounded preservation model for major stake-based consensus families.

These adapters do not claim that the listed production networks currently support
post-quantum validator credentials. They encode a conservative migration
obligation: replacing cryptographic authorization must not silently change stable
validator/economic identity, consensus weight, ownership, delegation, penalty
history, rewards, or the validator's membership window.

Chain-specific consensus correctness remains outside this bounded model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Iterable, Sequence


COMMON_PROTECTED = (
    "consensus_weight",
    "economic_owner",
    "reward_owner",
    "penalty_record",
    "delegation_state",
    "membership_window",
)


class MigrationStage(str, Enum):
    CLASSICAL = "CLASSICAL"
    PQ_REGISTERED = "PQ_REGISTERED"
    HYBRID_REQUIRED = "HYBRID_REQUIRED"
    PQ_PRIMARY = "PQ_PRIMARY"
    CLASSICAL_DISABLED = "CLASSICAL_DISABLED"


@dataclass(frozen=True)
class PosFamilyProfile:
    profile_id: str
    network: str
    consensus_family: str
    weight_semantics: str
    classical_consensus_credentials: tuple[str, ...]
    protected_fields: tuple[str, ...]
    identity_coupling: str
    reviewed_pq_status: str
    source_urls: tuple[str, ...]


@dataclass(frozen=True)
class FamilyValidatorState:
    profile_id: str
    stable_identity: str
    protected_state: tuple[tuple[str, str], ...]
    classical_credentials: tuple[str, ...]
    pq_credentials: tuple[str, ...] = ()
    stage: MigrationStage = MigrationStage.CLASSICAL

    def protected_map(self) -> dict[str, str]:
        return dict(self.protected_state)


@dataclass(frozen=True)
class FamilyProofReport:
    status: str
    claim_state: str
    profiles_checked: int
    transition_cases: int
    invalid_order_cases: int
    duplicate_weight_cases: int
    profiles: tuple[str, ...]
    proven_properties: tuple[str, ...]
    excluded_claims: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        for field in ("profiles", "proven_properties", "excluded_claims"):
            data[field] = list(data[field])
        return data


def _profile(
    profile_id: str,
    network: str,
    family: str,
    weight: str,
    credentials: tuple[str, ...],
    chain_fields: tuple[str, ...],
    identity_coupling: str,
    pq_status: str,
    sources: tuple[str, ...],
) -> PosFamilyProfile:
    return PosFamilyProfile(
        profile_id=profile_id,
        network=network,
        consensus_family=family,
        weight_semantics=weight,
        classical_consensus_credentials=credentials,
        protected_fields=COMMON_PROTECTED + chain_fields,
        identity_coupling=identity_coupling,
        reviewed_pq_status=pq_status,
        source_urls=sources,
    )


NO_PQ_CONSENSUS = "no PQ consensus migration confirmed in reviewed official sources"

PROFILES: dict[str, PosFamilyProfile] = {
    "ETHEREUM": _profile(
        "ETHEREUM", "Ethereum", "Gasper / Casper-FFG + LMD-GHOST",
        "effective-balance weighted finality",
        ("BLS validator signing key",),
        ("validator_index", "withdrawal_owner", "slashing_history"),
        "stable validator record with separately replaceable signing credential in WS migration model",
        "official PQ consensus roadmap active; production transition not complete",
        ("https://ethereum.org/roadmap/security/quantum-resistance/",),
    ),
    "SOLANA": _profile(
        "SOLANA", "Solana", "stake-weighted voting; Tower/Alpenglow transition",
        "delegated-stake weighted votes",
        ("Ed25519 authorized voter", "BLS validator key for Alpenglow transition"),
        ("vote_account", "stake_authority", "withdraw_authority", "vote_credits"),
        "vote/stake account indirection exists; consensus-key transition remains protocol-specific",
        "BLS transition confirmed; no PQ consensus migration confirmed in reviewed official sources",
        ("https://solana.com/staking", "https://solana.com/id/upgrades/bls-pubkey-vat"),
    ),
    "CARDANO": _profile(
        "CARDANO", "Cardano", "Ouroboros proof of stake",
        "stake-weighted leader election",
        ("KES operational key", "VRF key", "stake-pool cold credential"),
        ("stake_pool_identity", "pledge_and_delegated_stake", "reward_account", "kes_history"),
        "some pool identity is credential-coupled; protocol migration/indirection may be required",
        NO_PQ_CONSENSUS,
        ("https://docs.cardano.org/about-cardano/learn/ouroboros-overview", "https://docs.cardano.org/stake-pool-operators/creating-keys-and-certificates"),
    ),
    "POLKADOT": _profile(
        "POLKADOT", "Polkadot", "NPoS with BABE + GRANDPA",
        "nominated-stake selected validator set and finality authorities",
        ("BABE session key", "GRANDPA session key"),
        ("stash_identity", "nominator_backing", "session_assignment", "slash_record"),
        "session keys are associated with a stable stash/economic identity",
        NO_PQ_CONSENSUS,
        ("https://docs.polkadot.com/polkadot-protocol/architecture/polkadot-chain/pos-consensus/", "https://docs.polkadot.com/node-infrastructure/run-a-validator/onboarding-and-offboarding/key-management/"),
    ),
    "COMETBFT": _profile(
        "COMETBFT", "Cosmos / CometBFT PoS applications", "Tendermint/CometBFT BFT",
        "application-defined validator voting power; >2/3 commit",
        ("Ed25519/secp256k1/BLS12-381 consensus key depending configured key types",),
        ("validator_operator_identity", "bonded_power", "unbonding_state", "evidence_window"),
        "application/operator identity can be modeled separately from consensus public key",
        "current reviewed key types are classical; no PQ validator key type confirmed",
        ("https://docs.cosmos.network/cometbft/latest/docs/core/Validators", "https://docs.cosmos.network/cometbft/latest/spec/core/genesis"),
    ),
    "AVALANCHE": _profile(
        "AVALANCHE", "Avalanche Primary Network", "Avalanche/Snowman family with PoS sampling",
        "sampling probability proportional to stake",
        ("NodeID credential", "BLS proof-of-possession key"),
        ("node_economic_identity", "stake_amount", "staking_interval", "delegation_fee"),
        "NodeID/BLS identities are credential-linked; stable-economic mapping must be explicit",
        "no PQ validator credential migration confirmed in reviewed official sources",
        ("https://build.avax.network/docs/primary-network/validate/how-to-stake", "https://build.avax.network/docs/nodes/maintain/backup-restore"),
    ),
    "ALGORAND": _profile(
        "ALGORAND", "Algorand", "Pure Proof of Stake",
        "online-stake weighted VRF committee selection",
        ("participation/voting keys", "VRF selection key"),
        ("account_identity", "online_stake", "participation_validity", "state_proof_commitment"),
        "account identity is separate from participation keys and participation keys are renewable",
        "PQ account authorization is live; official docs state consensus participation is unchanged",
        ("https://dev.algorand.co/concepts/accounts/post-quantum/", "https://dev.algorand.co/concepts/protocol/registration/"),
    ),
    "NEAR": _profile(
        "NEAR", "NEAR", "proof of stake / sharded validator roles",
        "stake/delegation weighted validator selection",
        ("Ed25519 validator key in current reviewed tooling",),
        ("validator_account", "staked_balance", "delegator_state", "block_chunk_role"),
        "account/economic identity can be separated from operational validator credential in migration model",
        NO_PQ_CONSENSUS,
        ("https://docs.near.org/protocol/network/validators", "https://docs.near.org/web3-apps/tutorials/localnet/run"),
    ),
    "TEZOS": _profile(
        "TEZOS", "Tezos", "Tenderbake proof of stake",
        "baking power derived from staked/delegated tez",
        ("consensus key; BLS tz4 supported for aggregated attestations",),
        ("baker_identity", "baking_power", "staked_tez", "delegated_tez"),
        "explicit rotatable consensus key can change without moving stake/delegators",
        "classical/BLS consensus keys; no PQ consensus migration confirmed in reviewed official sources",
        ("https://docs.tezos.com/tutorials/join-dal-baker/prepare-account", "https://docs.tezos.com/architecture/bakers"),
    ),
    "APTOS": _profile(
        "APTOS", "Aptos", "AptosBFT stake-weighted validator set",
        "validator voting power derived from active stake",
        ("consensus public key with proof of possession",),
        ("stake_pool_address", "owner_identity", "active_stake", "pending_stake_state"),
        "framework exposes consensus-key rotation taking effect next epoch",
        "no PQ consensus scheme confirmed in reviewed official/framework sources",
        ("https://github.com/aptos-labs/aptos-core/blob/main/aptos-move/framework/aptos-framework/sources/stake.move",),
    ),
    "SUI": _profile(
        "SUI", "Sui", "Delegated PoS + Mysticeti consensus",
        "epoch committee voting power derived from delegated stake",
        ("validator protocol/consensus key material",),
        ("validator_address", "staking_pool", "epoch_voting_power", "commission_and_rewards"),
        "epoch validator identity and protocol keys are distinct concepts in the adapter; production rotation semantics require chain validation",
        NO_PQ_CONSENSUS,
        ("https://www.sui.io/validators", "https://github.com/MystenLabs/sui/blob/main/docs/content/develop/sui-architecture/sui-security.mdx"),
    ),
    "POLYGON_POS": _profile(
        "POLYGON_POS", "Polygon PoS", "Heimdall-v2 CometBFT + Bor block production",
        "stake-ratio validator selection; >=2/3 validating stake for milestone finality",
        ("Heimdall validator signer", "Bor secp256k1 block-producer signer"),
        ("staking_owner", "validator_stake", "delegated_stake", "checkpoint_and_milestone_history"),
        "official operations separate owner and signer responsibilities, while Heimdall/Bor signing remains classical",
        NO_PQ_CONSENSUS,
        ("https://docs.polygon.technology/pos/architecture/overview", "https://docs.polygon.technology/pos/how-to/validator/validator-binaries", "https://docs.polygon.technology/pos/architecture/bor/introduction"),
    ),
    "BNB_CHAIN": _profile(
        "BNB_CHAIN", "BNB Smart Chain", "Proof of Staked Authority (PoSA)",
        "stake-ranked validator election with active consensus set",
        ("consensus signing key", "BLS fast-finality vote key"),
        ("operator_address", "bonded_and_delegated_stake", "validator_role", "slash_history"),
        "operator address is stable while consensus and BLS vote addresses have explicit edit operations",
        NO_PQ_CONSENSUS,
        ("https://docs.bnbchain.org/bnb-smart-chain/validator/overview/", "https://docs.bnbchain.org/bnb-smart-chain/validator/manage-keys/", "https://docs.bnbchain.org/bnb-smart-chain/staking/developer-guide/"),
    ),
    "TRON": _profile(
        "TRON", "TRON", "Delegated Proof of Stake",
        "top-27 vote-ranked Super Representatives; 19-of-27 solidification condition",
        ("Witness/SR block-production signing key",),
        ("sr_account_identity", "vote_tally", "sr_rank_and_role", "reward_brokerage_state"),
        "witness permission can be delegated to a separate hot signing key while owner control remains offline",
        NO_PQ_CONSENSUS,
        ("https://developers.tron.network/docs/concensus", "https://developers.tron.network/docs/advanced-configuration-for-super-representative", "https://developers.tron.network/docs/sr-best-practices"),
    ),
    "CELESTIA": _profile(
        "CELESTIA", "Celestia", "Cosmos SDK + CometBFT proof of stake",
        "delegated TIA stake determines validator voting power",
        ("CometBFT validator consensus key",),
        ("validator_operator_identity", "bonded_tia", "delegator_positions", "validator_set_slot"),
        "chain-specific economic state sits above CometBFT consensus-key authorization",
        NO_PQ_CONSENSUS,
        ("https://docs.celestia.org/learn/TIA/staking-governance-supply/", "https://docs.cosmos.network/cometbft/latest/docs/core/Validators"),
    ),
    "FLOW": _profile(
        "FLOW", "Flow", "multi-role PoS with HotStuff/Jolteon consensus role",
        "role-specific stake with consensus-node voting security threshold",
        ("Flow node identity / consensus authorization material",),
        ("node_operator_identity", "node_role", "staked_flow", "delegated_flow"),
        "node role and stake are economic/protocol state distinct from the credential migration abstraction; exact key rotation requires protocol validation",
        NO_PQ_CONSENSUS,
        ("https://flow.com/node-validators", "https://flow.com/flow-tokenomics/technical-overview", "https://flow.com/protocol-autonomy-roadmap"),
    ),
    "HEDERA": _profile(
        "HEDERA", "Hedera", "stake-weighted hashgraph aBFT consensus",
        "node virtual-vote influence proportional to HBAR stake; >2/3 aggregate stake for consensus",
        ("node public key/certificate material", "Ed25519 node admin key"),
        ("node_id", "node_account_id", "staked_hbar", "proxy_stake_assignment"),
        "node identity/account/stake are explicit address-book state while cryptographic node/admin credentials are separately represented",
        NO_PQ_CONSENSUS,
        ("https://hedera.com/learning/how-hedera-works/", "https://docs.hedera.com/api-reference/network/get-the-network-address-book-nodes"),
    ),
    "TON": _profile(
        "TON", "The Open Network", "proof of stake with elector-selected validator sets",
        "effective stake determines validator election/weight within configured limits",
        ("validator public signing key", "ADNL networking key"),
        ("stake_holder_identity", "effective_stake", "election_round", "frozen_stake_and_complaint_history"),
        "official design separates validator signing key from the account supplying stake and supports per-election validator keys",
        NO_PQ_CONSENSUS,
        ("https://docs.ton.org/nodes/overview", "https://docs.ton.org/v3/documentation/network/config-params/update", "https://docs.ton.org/pdfs/ton.pdf"),
    ),
    "MULTIVERSX": _profile(
        "MULTIVERSX", "MultiversX", "Secure Proof of Stake (SPoS)",
        "stake-eligible validators with VRF-style selection and BLS multisignature finality",
        ("long-lived BLS validator key",),
        ("staking_wallet_identity", "staked_egld", "reward_address", "shard_assignment"),
        "validator BLS key is distinct from the wallet key controlling stake; reward address is separately configurable",
        NO_PQ_CONSENSUS,
        ("https://docs.multiversx.com/learn/consensus/", "https://docs.multiversx.com/validators/key-management/protect-keys/", "https://docs.multiversx.com/validators/staking/staking-smart-contract/"),
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_state(state: FamilyValidatorState) -> None:
    _require(state.profile_id in PROFILES, "unknown PoS family profile")
    _require(bool(state.stable_identity), "stable identity is required")
    protected = state.protected_map()
    required = set(PROFILES[state.profile_id].protected_fields)
    missing = sorted(required.difference(protected))
    _require(not missing, f"missing protected fields: {missing}")
    try:
        weight = int(protected["consensus_weight"])
    except (KeyError, ValueError) as exc:
        raise ValueError("consensus_weight must be an integer string") from exc
    _require(weight >= 0, "consensus_weight must be non-negative")


def protected_projection(state: FamilyValidatorState) -> tuple[str, tuple[tuple[str, str], ...]]:
    validate_state(state)
    return state.stable_identity, tuple(sorted(state.protected_state))


def register_pq(state: FamilyValidatorState, credential: str) -> FamilyValidatorState:
    validate_state(state)
    _require(state.stage is MigrationStage.CLASSICAL, "PQ registration requires CLASSICAL stage")
    _require(bool(credential), "PQ credential is required")
    return replace(state, pq_credentials=(credential,), stage=MigrationStage.PQ_REGISTERED)


def require_hybrid(state: FamilyValidatorState) -> FamilyValidatorState:
    _require(state.stage is MigrationStage.PQ_REGISTERED, "hybrid requires PQ_REGISTERED stage")
    return replace(state, stage=MigrationStage.HYBRID_REQUIRED)


def activate_pq(state: FamilyValidatorState) -> FamilyValidatorState:
    _require(state.stage is MigrationStage.HYBRID_REQUIRED, "PQ primary requires HYBRID_REQUIRED stage")
    return replace(state, stage=MigrationStage.PQ_PRIMARY)


def sunset_classical(state: FamilyValidatorState) -> FamilyValidatorState:
    _require(state.stage is MigrationStage.PQ_PRIMARY, "classical sunset requires PQ_PRIMARY stage")
    return replace(state, stage=MigrationStage.CLASSICAL_DISABLED)


def migrate(state: FamilyValidatorState, credential: str) -> tuple[FamilyValidatorState, ...]:
    s1 = register_pq(state, credential)
    s2 = require_hybrid(s1)
    s3 = activate_pq(s2)
    s4 = sunset_classical(s3)
    return s1, s2, s3, s4


def vote_weight_once(states: Sequence[FamilyValidatorState], identities: Iterable[str]) -> int:
    seen = frozenset(identities)
    unique: dict[str, FamilyValidatorState] = {}
    for state in states:
        validate_state(state)
        _require(state.stable_identity not in unique, "duplicate stable identity in validator set")
        unique[state.stable_identity] = state
    return sum(
        int(state.protected_map()["consensus_weight"])
        for identity, state in unique.items()
        if identity in seen
    )


def _sample_state(profile: PosFamilyProfile, variant: int) -> FamilyValidatorState:
    protected: dict[str, str] = {}
    for field in profile.protected_fields:
        if field == "consensus_weight":
            protected[field] = str((variant + 1) * 100)
        else:
            protected[field] = f"{profile.profile_id.lower()}-{field}-{variant}"
    return FamilyValidatorState(
        profile_id=profile.profile_id,
        stable_identity=f"{profile.profile_id.lower()}-validator-{variant}",
        protected_state=tuple(sorted(protected.items())),
        classical_credentials=profile.classical_consensus_credentials,
    )


def run_family_preservation_proof() -> FamilyProofReport:
    transitions = 0
    invalid = 0
    duplicate_weight = 0

    for profile in PROFILES.values():
        migrated_states: list[FamilyValidatorState] = []
        for variant in range(2):
            base = _sample_state(profile, variant)
            before = protected_projection(base)
            path = migrate(base, f"ML-DSA-65:{profile.profile_id}:{variant}")
            for stage in path:
                if protected_projection(stage) != before:
                    raise AssertionError(f"{profile.profile_id} protected state changed during migration")
                transitions += 1
            migrated_states.append(path[-1])

            try:
                sunset_classical(base)
            except ValueError:
                invalid += 1
            else:
                raise AssertionError(f"{profile.profile_id} accepted CLASSICAL -> CLASSICAL_DISABLED")

        identities = [state.stable_identity for state in migrated_states]
        expected = sum(int(state.protected_map()["consensus_weight"]) for state in migrated_states)
        if vote_weight_once(migrated_states, identities + identities) != expected:
            raise AssertionError(f"{profile.profile_id} hybrid credentials inflated consensus weight")
        duplicate_weight += 1

    return FamilyProofReport(
        status="PASS",
        claim_state="BOUNDED_MULTI_POS_MIGRATION_PRESERVATION_PROVEN_IN_SOFTWARE",
        profiles_checked=len(PROFILES),
        transition_cases=transitions,
        invalid_order_cases=invalid,
        duplicate_weight_cases=duplicate_weight,
        profiles=tuple(PROFILES),
        proven_properties=(
            "Credential-stage migration cannot alter each adapter's declared protected economic/consensus projection.",
            "Consensus weight is counted once per stable validator identity in the bounded model.",
            "Direct classical-to-sunset migration fails closed for every profile.",
            "Chain-specific protected fields are required before a profile can enter the proof domain.",
        ),
        excluded_claims=(
            "No claim that every production network currently supports PQ validator credentials.",
            "No proof of any listed network's production consensus implementation, liveness, finality, fork choice, VRF, aggregation, randomness, networking, or throughput under PQ load.",
            "No claim that a cryptographically coupled production identity can be migrated without a protocol upgrade.",
            "No mainnet/testnet transaction, validator change, stake movement, or live key rotation is performed.",
            "No claim that this finite adapter set literally enumerates every proof-of-stake or stake-weighted consensus network in existence.",
        ),
    )
