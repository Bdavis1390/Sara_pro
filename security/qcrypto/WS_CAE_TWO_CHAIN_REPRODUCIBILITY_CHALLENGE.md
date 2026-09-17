# WS-CAE Two-Chain Reproducibility Challenge

Status date: 2026-09-13

## Objective

Test whether WS-CAE is sufficiently precise for an independent reviewer or implementation to classify two unrelated blockchain account models without access to hidden Worldshepherd state.

A successful result is not agreement by assertion. The reviewer must show how each conclusion follows from public evidence and must preserve disagreements.

## Required ecosystems

Use at least two ecosystems with materially different account architectures. Preferred initial pair:

- Algorand native rekey / PQ account authorization;
- Ethereum account abstraction / EIP-8141 direction.

A Sui address-alias profile may be substituted or added.

## Required outputs per ecosystem

The reviewer should independently determine:

1. whether authority identity remains stable across authenticator replacement;
2. whether authenticator replacement is live, testnet-only, draft, roadmap, or absent;
3. whether PQ account/vault authorization is live;
4. whether policy or quorum semantics are independently replaceable from the authenticator;
5. whether a recovery mechanism is documented and independently testable;
6. whether replay/domain separation is explicit;
7. whether evidence can distinguish roadmap from deployed capability;
8. whether consensus/validator authentication remains classically exposed;
9. the highest WS-CAE conformance state supportable by evidence;
10. unresolved ambiguity or disagreement with the WS-CAE interpretation.

## Pass criteria

The challenge is considered independently reproduced when:

- two ecosystems are evaluated from public evidence;
- the reviewer does not use private Worldshepherd context;
- roadmap capability is not promoted to live capability;
- account-level PQ readiness is not promoted to consensus-level PQ security;
- stable authority and authenticator replaceability are evaluated separately;
- disagreements are recorded rather than normalized away;
- the resulting evidence is public or independently inspectable;
- at least one materially independent reviewer or implementation signs or otherwise attributes the result to itself.

## Stronger result

A stronger milestone is achieved if two independent implementations consume the same public evidence and independently produce materially equivalent authority-state classifications for two chains.

That would support promotion from `RESEARCH_SPEARHEAD` toward `EXTERNALLY_REPRODUCED_PROFILE`.

## Failure is useful

The challenge should fail if the profile is ambiguous, chain-specific, impossible to reproduce, or materially overlaps an existing public standard that already performs the same role. Such a failure narrows or invalidates the lead claim and should be preserved as evidence.

## Claims boundary

Passing this challenge would demonstrate reproducibility of the WS-CAE semantic model. It would not demonstrate standards-body adoption, production security certification, full-chain post-quantum security, or cryptographic correctness of any underlying signature implementation.
