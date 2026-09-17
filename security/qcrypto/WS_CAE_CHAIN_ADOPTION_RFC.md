# WS-CAE Chain Adoption RFC

Status: research proposal for voluntary interoperability adoption.

## Proposal

A blockchain ecosystem MAY publish a WS-CAE authority profile describing its current authority-agility and post-quantum migration state.

Adoption requires no consensus change, signature-scheme change, wallet migration, validator change, or Worldshepherd runtime.

The smallest useful adoption consists of:

1. copy `examples/ws_cae_chain_profile_template.json`;
2. replace placeholders with the ecosystem's current documented state;
3. link supporting evidence in adjacent documentation or repository records;
4. validate the profile with `ws_cae_cli.py` or the reusable GitHub action;
5. update the profile whenever maturity changes.

## Why a chain benefits even before PQ deployment

WS-CAE explicitly supports `ROADMAP`, `DRAFT`, `DEVNET`, `TESTNET`, and `MAINNET` maturity plus `NONE`, `PLUGGABLE_AUTH_ONLY`, `PQ_NON_MAINNET`, and `PQ_MAINNET` authorization states.

A chain therefore does not need to claim a capability it has not shipped. Publishing a truthful gap is still useful because custodians, wallets, auditors, exchanges, and migration programs can stop rediscovering the same facts independently.

## Consumer independence

Chains publish facts. Consumers publish requirements.

The consumer-policy schema lets a relying party define minimum maturity, acceptable PQ authorization states, accepted consensus states, and requirements for stable authority, replaceable authentication, policy, recovery, replay/domain separation, and evidence.

A chain profile remains unchanged when different consumers choose different risk policies.

## Equivalent-evidence clause

WS-CAE should not become a lock-in requirement.

A relying party using WS-CAE is encouraged to accept equivalent evidence in another format when it provides the same authority-state information and preserves maturity and consensus boundaries.

This makes the economic argument for adoption about lower duplicated diligence cost rather than mandatory dependence on the reference implementation.

## Chain-side implementation burden

At the profile-only level, the burden is documentation and evidence maintenance.

At the CI level, the burden is one read-only conformance step. The reference action has no key-generation, signing, wallet-access, transaction-construction, broadcast, or asset-movement capability.

No chain-specific SDK is required by the reference implementation.

## Expected downstream uses

A published profile can be consumed by:

- custody onboarding and asset-support review;
- exchange listing/security review;
- wallet migration planning;
- treasury and institutional due diligence;
- insurer and auditor evidence collection;
- PQ migration roadmaps and dependency inventories;
- cross-chain risk engines that need one vocabulary across heterogeneous account models.

## Conditions under which adoption should be rejected

A chain should not adopt WS-CAE merely for marketing if it cannot maintain truthful evidence or if the profile would obscure rather than clarify its security model.

The profile is valuable only if roadmap capabilities remain distinct from deployed capabilities and account/vault authorization remains distinct from consensus/validator security.

## Proposed adoption signal

A project can describe its state using evidence rather than a promotional badge:

- `PROFILE_PUBLISHED` — a schema-conformant profile exists;
- `CI_VALIDATED` — the profile passes a reproducible conformance check;
- `POLICY_EVALUATED` — at least one relying-party policy has been run against it;
- `INDEPENDENTLY_REPRODUCED` — a party independent of the profile author has reproduced or publicly disputed the classification.

These states indicate process maturity only. They are not security certifications.

## Rationale

The economic case is intentionally simple: a chain already has an authority model that external institutions must understand. Publishing that state once in a neutral, machine-readable profile is generally lower cost than requiring every custodian, wallet, exchange, auditor, and migration program to reconstruct the same facts separately.

Non-adoption remains a legitimate choice. The objective is to make the alternative visibly more expensive in duplicated diligence while keeping adoption technically non-invasive and vendor-neutral.
