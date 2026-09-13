# Worldshepherd QCRYPTO Risk Gate

This package implements defensive, claims-controlled quantum-cryptography migration planning.

QCRYPTO keeps attack-resource estimates, hardware roadmaps, QEC/platform maturity, decoder capacity, protocol-mitigation maturity, mainnet proof maturity, and migration timelines separate. A roadmap is not Q-day; a mainnet proof is not network-wide migration; an account-layer deployment is not full-protocol quantum resilience.

## Current cross-ecosystem horizon signal

The current planning comparison uses 2028 as an aggressive external risk horizon because IonQ's published 2028 hardware roadmap numerically overlaps its own published secp256k1 attack-resource envelope. This remains forward-looking planning evidence, not demonstrated attack capability.

Against that planning horizon:

- Bitcoin's BIP-361 nominal full legacy-signature sunset is approximately five years after activation; an immediate 2026 start would reach roughly 2031, about three years after the planning horizon.
- Ethereum targets completion of core post-quantum infrastructure around 2029, while execution-layer and wider ecosystem migration extends beyond that.
- Algorand targets broad quantum resilience by the end of 2027 and already has native Falcon-1024 accounts live, but consensus-level post-quantum work remains incomplete.

QCRYPTO therefore treats the portfolio state as `MULTI_ECOSYSTEM_MIGRATION_DEFICIT`: multiple major ecosystems have roadmap/sunset targets beyond the aggressive planning horizon, while the one nominally inside the horizon still has incomplete protocol scope.

The operational implication is parallel migration engineering across protocol, wallet, custody, validator, relay, recovery, and governance layers rather than serial migration.

## Claims boundary

No production cryptographic break, Q-day, guaranteed roadmap delivery, or full-protocol quantum safety is claimed by this package.
