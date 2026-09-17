# QCRYPTO Signet + Hoodi host profile

This profile is for the observer-first public-testnet deployment only. It is not a validator-key host and contains no live-value signing authority.

## Recommended initial host

- x86_64 Linux
- 4+ fast CPU cores
- 32 GB RAM
- 4 TB NVMe SSD preferred
- unmetered/reliably high-bandwidth network
- persistent volumes for Bitcoin Signet, Ethereum execution, and Ethereum consensus data
- accurate system clock
- SSH/admin access restricted to the operator

For later Hoodi validator testing, plan for 8+ CPU cores and 64 GB RAM if following the more conservative validator hardware guidance. Validator signing keys remain outside this observer deployment and require a separately approved external-signer/HSM workflow.

## Why this profile is intentionally not tiny

Ethereum's current operator guidance identifies storage I/O as the principal bottleneck. Current guidance lists 2+ CPU cores, 16 GB RAM, and 2 TB NVMe as a minimum baseline, while recommending a fast 4+ core CPU, 32 GB RAM, and 4 TB NVMe for a full node; validator workloads require more headroom.

The public-testnet host is an integration proving ground, not the desired decentralization end-state. Long-term Worldshepherd design should preserve the ability for operators to verify protocol state independently on self-controlled hardware rather than depending on a single cloud provider.

## Network exposure

The observer package publishes no Bitcoin RPC, Ethereum execution RPC, or Engine API to the public host interface. The Hoodi beacon status API is bound to host loopback (`127.0.0.1:5052`) only for measured deployment verification.

No mainnet port or mainnet flag is part of the package.
