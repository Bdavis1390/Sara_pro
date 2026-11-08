# Cross-crypto PQ migration evidence — 2026-09-13

This note records why WS-CAE now models cryptocurrency as a dependency system rather than a chain-only property.

## Sector coordination

U.S. Treasury launched the Quantum-Readiness Task Force on 2026-08-24 with three workstreams: Sector Alignment & PQC Transition; Third-Party & Vendor Readiness; and Digital Assets and Emerging Technology Risk.

Source: https://home.treasury.gov/news/press-releases/sb0615

Interpretation: digital assets are explicitly inside a broader financial-sector PQ migration program. This is coordination evidence, not a crypto-specific binding deadline.

## Chain / execution layer

Ethereum documents separate quantum-vulnerable planes for account signatures, consensus BLS, commitments/data availability, and application-layer proof systems, with a structured roadmap toward full PQ protection.

Source: https://ethereum.org/roadmap/security/quantum-resistance/

Interpretation: even one chain contains multiple cryptographic dependency planes; account migration alone is not full-chain migration.

## Stablecoin / application layer

Circle states that Arc already supports SLH-DSA for developers, while transaction signing remains ECDSA and Arc has not selected a final PQ transaction signature scheme.

Source: https://www.circle.com/blog/the-quantum-gap-is-closing

Interpretation: application/PQ primitive support and transaction-authority migration can mature at different rates.

## Proof / cross-chain infrastructure

LayerZero introduced Akita on 2026-09-09 as a production-ready lattice-based post-quantum polynomial commitment scheme intended for proof systems.

Source: https://layerzero.network/blog/introducing-akita

LayerZero also documents bridge security as a separate attestation/trust problem from the security of either endpoint chain.

Source: https://layerzero.network/blog/cross-chain-bridge-security

Interpretation: proof-system and bridge/message verification dependencies must be modeled separately from chain account signatures.

## Institutional custody

BitGo launched Bitcoin quantum-risk management capabilities for institutional wallets and separately completed a post-quantum MPC transaction simulation with Silence Laboratories.

Sources:
- https://investors.bitgo.com/news/news-details/2026/BitGo-Announces-New-Quantum-Risk-Management-Capabilities-for-Bitcoin-Wallets/default.aspx
- https://investors.bitgo.com/news/news-details/2026/BitGo-and-Silence-Laboratories-Complete-First-Post-Quantum-MPC-Transaction-Simulation-by-a-Regulated-Custodian/default.aspx

Interpretation: custody migration can progress independently from chain-native PQ authorization. Simulation does not equal production live-chain PQ signing.

## Self-custody / device layer

Ledger added ML-KEM and ML-DSA APIs to its SDK in 2026.

Source: https://www.ledger.com/blog-post-quantum-cryptography-ledger-sdk

Trezor Safe 7 uses PQ cryptography for device authentication/boot/firmware integrity but explicitly states that full crypto protection still requires blockchain upgrades.

Source: https://trezor.io/guides/trezor-devices/trezor-safe-7/the-first-quantum-ready-hardware-wallet

Interpretation: device integrity can be PQ-ready while asset transaction authorization remains classical.

## Governance and exchange/custody coordination

Coinbase's Quantum Advisory Council has called for ecosystem-level planning around migration and abandoned/vulnerable assets, while Coinbase has separately described its own post-quantum preparations.

Sources:
- https://www.coinbase.com/blog/coinbase-quantum-advisory-council-post-quantum-migration-and-abandoned-coins
- https://www.coinbase.com/blog/what-coinbase-is-doing-to-prepare-for-post-quantum-cryptography

Interpretation: governance, exchange/custody operations, wallet support, and chain activation are distinct migration dependencies.

## WS-CAE consequence

These sources support the architectural conclusion that cryptocurrency PQ readiness is multi-layer and asynchronous. They do not support a claim that any cryptocurrency is currently fully quantum-safe or that a cryptographically relevant quantum computer exists today.

WS-CAE therefore evaluates declared critical dependencies independently and reports the weakest verified state instead of inheriting the best-looking chain-level state.
