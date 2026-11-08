# WS-CAE Consensus Continuity

Status: research/interoperability profile. Read-only metadata only.

WS-CAE now treats consensus as a separate migration plane from account or asset authorization. A chain can have post-quantum account authorization while its validator, farmer, miner, finality, randomness, resource-proof, or consensus-signature plane remains classical or unproven.

## Separate planes

The consensus profile records:

- consensus family and named mechanism;
- Sybil/resource mechanism (`WORK`, `STAKE`, `STORAGE_SPACE`, `CAPACITY`, `COVERAGE`, `AUTHORITY`, etc.);
- finality model;
- participant/validator authentication primitive;
- participant-key agility;
- local/self-validation model;
- consensus PQ state;
- resource-proof migration/agility;
- primary evidence.

`PoC` is not accepted as an unqualified mechanism name. `Proof of Capacity` and `Proof of Coverage` are materially different and must be declared explicitly. `Proof of History` is modeled as an auxiliary history/clock mechanism and cannot by itself satisfy the consensus-family field.

## Self-validation boundary

Local/self-validation is not consensus.

A full node may independently validate blocks or re-execute state while network agreement still depends on classical validator signatures. Conversely, a light client may verify a compact proof without independently replaying all execution. WS-CAE therefore records local validation separately from network consensus authentication.

This distinction prevents `self-validating` from being used as a substitute for evidence that the network's validator/finality key plane has migrated.

## Current reference observations

### Bitcoin

Bitcoin full nodes independently validate their own block chain and consensus rules; proof of work supplies the resource/Sybil-resistance plane.

Primary sources:
- https://developer.bitcoin.org/devguide/block_chain.html
- https://developer.bitcoin.org/devguide/operating_modes.html

### Ethereum

Ethereum uses proof of stake with Gasper (Casper-FFG + LMD-GHOST). Validators use a distinct BLS signing-key plane for proposals and attestations, separate from ordinary execution-account keys. Execution clients re-execute transactions/state while consensus clients and validators handle the consensus layer.

Primary sources:
- https://ethereum.org/developers/docs/consensus-mechanisms/pos/
- https://ethereum.org/developers/docs/consensus-mechanisms/pos/keys
- https://ethereum.org/developers/docs/consensus-mechanisms/pos/gasper/

### Solana

Solana documents a proof-of-stake consensus design using Tower BFT, with Proof of History acting as a global clock before consensus. WS-CAE therefore must not classify Proof of History alone as the consensus family.

Primary source:
- https://solana.com/developers/migrate-to-solana/consensus

### Polkadot

Polkadot uses Nominated Proof of Stake to select validators, BABE for block production, and GRANDPA for deterministic finality. Block production and finality are therefore separately identifiable consensus subplanes.

Primary source:
- https://docs.polkadot.com/reference/polkadot-hub/consensus-and-security/pos-consensus/

### Chia

Chia uses Proof of Space and Time: storage capacity supplies the scarce resource, VDFs supply proofs of time, and farmer signatures are BLS. Chia documentation explicitly distinguishes its proof of space from Proof of Capacity. Full block validation separately checks consensus rules and transaction/body validity.

Primary sources:
- https://docs.chia.net/consensus-basics/
- https://docs.chia.net/chia-blockchain/consensus/consensus-intro/
- https://docs.chia.net/chia-blockchain/consensus/block-validation/block-validation/

### CometBFT/Cosmos SDK ecosystems

CometBFT validators commit blocks by broadcasting cryptographically signed votes. Proof of stake is not intrinsic to CometBFT itself; an application may layer stake or another validator-selection rule on top. WS-CAE therefore separates BFT consensus/authentication from the economic selection mechanism.

Primary sources:
- https://docs.cosmos.network/cometbft/latest/docs/core/Validators
- https://docs.cosmos.network/cometbft/latest/spec/consensus/Overview

### Avalanche

Avalanche validators secure the network using stake-weighted validator participation; current validator onboarding includes a node ID plus BLS key/signature. This creates a consensus-authentication plane distinct from ordinary asset authorization.

Primary source:
- https://docs.avax.network/docs/primary-network/validate/how-to-stake

### Proof of Coverage lifecycle caution

Helium's official documentation states that Proof of Coverage was removed from the Helium networks on July 6, 2026 and its PoC data types are now retained only for historical reference. A current-state model must therefore not infer present consensus/security from historical PoC documentation.

Primary source:
- https://docs.helium.com/network-data/oracle-data/

## Full-stack PQ gate

`FULL_STACK_PQC_READY_CANDIDATE` now requires a valid consensus-continuity profile in addition to mainnet PQ asset authorization. A chain-profile flag alone is insufficient. The consensus profile must establish internally consistent PQ participant-key agility and a documented local/self-validation model.

This remains a research classification, not certification, standards adoption, or a claim that any named chain is fully post-quantum secure.
