# Bitcoin post-quantum mitigation dependency note — 2026-09-12

## Decision

Classify the current Bitcoin mitigation landscape as:

`DEPENDENCY_COMPLETE_RESEARCH_STACK`

with urgency:

`ACCELERATE_SECURITY_PROOF_INTEROP_AND_ACTIVATION_PLANNING`

This is **not** a claim that Bitcoin has a deployed post-quantum transaction path.

## Why this changed

Three public lines of work now form a recognizable end-to-end mitigation sequence:

1. **SHRINCS** proposes a compact hash-based signature scheme for Bitcoin transaction authorization and includes an executable reference specification.
2. **DropKick** proposes a commit/reveal rescue path for legacy coins after a quantum transition.
3. **BIP-361** proposes a phased sunset for legacy ECDSA/Schnorr signatures after a PQ output/signature path exists.

The important finding is the dependency relationship, not the existence of three proposals. DropKick's author explicitly states that an on-chain PQ signature/address mechanism must already exist before the rescue protocol can help. BIP-361 likewise requires a future post-quantum signature BIP.

Therefore the mitigation stack is conceptually connected but **not deployable**.

## SHRINCS maturity boundary

The current SHRINCS draft reports a 48-byte public key, stateful signatures ranging from 548 to 4,619 bytes, and a 5,777-byte stateless fallback signature. The stateful path is intended to reduce block-space cost, while the stateless path provides a recovery option when signing state cannot be trusted.

However, the public draft also states that:

- the security proof is TODO;
- comprehensive test vectors are TODO;
- the pure-Python reference implementation is non-constant-time and for demonstration only;
- the reference implementation does not provide production state management;
- an optimized production implementation remains TODO.

Those gaps are blockers for production or consensus-readiness claims.

## Required upgrade order

The current evidence supports this dependency order:

`security proof + test vectors`
→ `independent implementations + interoperability`
→ `wallet/state-management validation`
→ `production node/wallet implementation`
→ `PQ authorization/output activation`
→ `legacy rescue activation`
→ `legacy-signature sunset`

Rescue and sunset work should continue in parallel, but they cannot substitute for the missing PQ authorization/output layer.

## Worldshepherd control

`bitcoin_mitigation_readiness.py` machine-enforces the distinction between:

- executable draft;
- production implementation;
- consensus activation;
- rescue dependency;
- sunset dependency; and
- deployable mitigation stack.

A reference implementation alone can never return `DEPLOYABLE_MITIGATION_STACK`.

## Claims state

- SHRINCS compact PQ signature design: **PUBLIC DRAFT / EXECUTABLE SPECIFICATION**.
- SHRINCS production readiness: **NOT ESTABLISHED**.
- DropKick rescue: **PUBLIC PROPOSAL / DEPENDENCY-BLOCKED**.
- BIP-361 legacy sunset: **DRAFT / DEPENDENCY-BLOCKED**.
- Bitcoin full PQ migration stack: **NOT DEPLOYED**.

The correct operational response is to accelerate proof completion, test vectors, interoperability, wallet state-safety, and activation engineering while preserving the existing claims-control boundary.
