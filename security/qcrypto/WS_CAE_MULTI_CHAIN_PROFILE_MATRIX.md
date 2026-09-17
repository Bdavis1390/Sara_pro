# WS-CAE Multi-Chain Authority Profile Matrix

Status date: 2026-09-13

## Purpose

Demonstrate that the same authority vocabulary can describe materially different blockchain account architectures without changing the meaning of the fields.

This is a research mapping, not a chain endorsement or security certification.

| Ecosystem | Stable authority identity | Replaceable authentication | PQ account authorization | Policy/quorum layer | Deployment maturity | Consensus/validator PQ boundary | WS-CAE interpretation |
|---|---|---|---|---|---|---|---|
| Algorand | Yes: account address can remain unchanged through rekeying | Live native rekey semantics | Falcon-1024 account authorization is supported after the relevant network upgrade | Native PQ multisig is not provided; delegated logic can express additional controls | Native PQ account/rekey path is implemented at protocol level; ecosystem tooling support varies | Consensus participation is explicitly unchanged | Strong live `NATIVE_REKEY` adapter foundation; account-level PQ capability must not be promoted to PQ consensus |
| Ethereum | Intended by native account-abstraction direction | EIP-8141 unlinks accounts from ECDSA keys and enables native key rotation | EIP-8141 is an enabling substrate, not itself a single mandated PQ signature scheme | Programmable validation is central to Frame Transactions | EIP-8141 is S-tier / must-ship for Hegotá, but not treated here as already activated on mainnet | Ethereum separately targets execution, consensus, and data-layer PQ migration | Strong scheduled `NATIVE_ACCOUNT_ABSTRACTION` adapter direction; maturity remains scheduled rather than live |
| Sui | Yes: address aliases preserve the account address while authorization changes | Address aliases are already live | ML-DSA native account authentication is planned; SLH-DSA vault path is separate | Move vaults can express high-value policy separately from native account authentication | Address-alias substrate is live; PQ account/vault milestones remain on the published rollout schedule | Account/vault migration does not by itself establish PQ consensus | Live `ADDRESS_ALIAS` substrate with roadmap/testnet/mainnet PQ milestones tracked separately |
| Shell Chain | Yes: documentation states address remains stable across key rotation | Native account-specific validation is replaceable | Documentation reports native PQ signature validation | Custom validators can express multisig/recovery/time-lock policy | Public testnet and native-AA implementation are reported; mainnet maturity is tracked separately | Account authorization claims must remain distinct from validator/consensus claims | Strong `NATIVE_ACCOUNT_ABSTRACTION` implementation example, but single-chain rather than a cross-chain conformance model |

## Common semantics demonstrated

Across all four profiles, the following questions remain meaningful without changing definitions:

1. Is the authority identifier stable when authentication changes?
2. Is authenticator replacement live, scheduled, testnet-only, or roadmap-only?
3. Is post-quantum authorization itself live?
4. Is authorization policy separable from the cryptographic authenticator?
5. What recovery capability exists?
6. What replay/domain binding exists?
7. What evidence supports the maturity state?
8. Does the account/vault result leave consensus or validator cryptography outside the protection boundary?

The account mechanics differ substantially, but the authority-state questions do not. That is the interoperability thesis WS-CAE is designed to test.

## Lead significance

A chain-specific implementation can answer these questions for itself. WS-CAE's proposed value is that custodians, auditors, wallet providers, risk engines, and migration programs can ask the same questions across unrelated chains and compare the answers without pretending the underlying mechanisms are identical.

## Claims boundary

This mapping is based on public project and protocol documentation current to the status date. Scheduled capabilities are not treated as deployed. Testnet capability is not treated as mainnet capability. Account-level PQ capability is not treated as consensus-level PQ security.
