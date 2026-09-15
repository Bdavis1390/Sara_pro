# Worldshepherd Proof of Ownership (PoO) v1

**Status:** experimental internal ownership-attestation design
**Schema:** `WS-POO-V1`

## Thesis

Worldshepherd PoO combines four independent evidence gates:

`PoO = CONTROL ∧ PROVENANCE ∧ WORK ∧ BONDED_STAKE`

- **CONTROL** — fresh challenge evidence that the claimant controls the asserted credential/key.
- **PROVENANCE** — evidence linking the claimant/key to the asset record.
- **WORK (PoW)** — bounded computational work attached to the claim as anti-spam/replay cost.
- **BONDED STAKE (PoS)** — externally attested locked collateral/accountability associated with the claim.

PoW and PoS strengthen the claim but do not create ownership by themselves.

## Claims boundary

PoO can support a cryptographic/provenance ownership claim. It does **not** by itself establish:

- legal title;
- beneficial ownership;
- government registration;
- regulatory compliance;
- court-recognized property rights;
- authority to seize, transfer, freeze, or spend an asset.

The strongest v1 software label is `REGISTRY_LINKED_OWNERSHIP_CLAIM`, and even that label keeps `legal_title_established = false`.

## Why combine PoW and PoS?

### PoW contribution

A bounded claim-specific PoW challenge makes mass fraudulent claims and replay campaigns more expensive. Work is domain-separated to the canonical ownership claim digest and is policy-limited rather than intended to reproduce cryptocurrency mining.

### PoS contribution

A bonded-stake attestation puts accountable collateral behind a claim. The stake is useful only when its lock/escrow/ledger attestation is independently verified. A numeric amount supplied by a claimant is never sufficient evidence.

### Actual ownership evidence

The primary evidence remains claimant control plus provenance. A trusted external registry can strengthen that linkage, but the legal meaning of the registry remains outside this evaluator.

## Worldshepherd mapping

- **ECHO** — custody/provenance references, evidence digests, registry/stake-attestation references, history.
- **PRIME SENTINEL** — required PoW difficulty, stake policy, allowed stake units, challenge freshness, dispute/slash policy.
- **SARA** — bounded workflow orchestration and explicit human approval. SARA does not transfer the underlying asset merely because PoO passes.
- **OVERWATCH** — dashboards for pending, verified, registry-linked, disputed, expired, transferred, and revoked claims.

## Recommended lifecycle

1. `DRAFT_CLAIM`
2. `CONTROL_CHALLENGE_PENDING`
3. `PROVENANCE_REVIEW_PENDING`
4. `WORK_PENDING`
5. `STAKE_BOND_PENDING`
6. `BONDED_CRYPTOGRAPHIC_OWNERSHIP_CLAIM`
7. optionally `REGISTRY_LINKED_OWNERSHIP_CLAIM`
8. `DISPUTED`, `EXPIRED`, `TRANSFERRED`, or `REVOKED`

No lifecycle state grants legal title or execution authority by itself.

## Transfer rule

Future transfer support should require an append-only successor claim linked to the previous claim digest plus explicit transfer authorization evidence. Ownership history should never be rewritten in place.

## Double-claim / dispute rule

Conflicting active claims for the same asset should produce `DISPUTED`, not an automatic winner. PoW amount and stake size must not override contradictory authoritative evidence.

## Slashing rule

A future stake/slash engine may recommend loss of bond for policy-defined false or contradictory claims, but Worldshepherd must not autonomously confiscate value. Any actual slash requires an independently authorized external mechanism.

## Security posture

PoO is intentionally a gated evidence protocol, not a weighted reputation score. A wealthy claimant cannot buy ownership merely by staking more, and a claimant with more compute cannot mine ownership into existence.
