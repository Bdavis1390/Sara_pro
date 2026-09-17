# WS-CAE Adoption Case

Status: research deployment profile; not a standards-body specification.

## Why adopt

WS-CAE is designed so a blockchain, wallet platform, or custody stack can publish a machine-readable description of its authority-agility state without changing consensus, changing signature algorithms, adding a Worldshepherd runtime, or adopting a vendor-specific cryptographic library.

The minimum adoption act is one JSON profile conforming to `ws_cae_profile.schema.json`.

That profile lets relying parties compare otherwise incompatible account models using the same questions:

- Is authority identity stable when authentication changes?
- Can authentication be replaced?
- What is actually deployed versus roadmap, draft, devnet, or testnet?
- Is PQ account authorization deployed, merely pluggable, or absent?
- Are policy, recovery, replay/domain separation, and evidence documented?
- Does the result leave consensus or validator cryptography outside the protection boundary?

## Adoption cost model

### Level 0 — publish a profile

Publish a single WS-CAE JSON document and evidence links in project documentation or a repository. No chain change is required.

### Level 1 — validate in CI

Run the read-only WS-CAE action against the profile. The action has no wallet, signing, transaction, or asset-movement capability.

### Level 2 — expose profiles to relying parties

Custodians, exchanges, wallets, treasuries, auditors, and risk engines can consume the same profile while applying their own `ws_cae_policy.schema.json` policy. The chain does not have to maintain a different questionnaire for every relying party.

### Level 3 — independently reproduce

An independent reviewer consumes the public profile and supporting evidence and either reproduces the classification or records a reasoned disagreement.

## Why the incentive is asymmetric

A chain that adopts WS-CAE incurs a small documentation and CI cost but gains a reusable authority-agility representation for many downstream consumers.

A chain that does not adopt remains fully free to use any account model or cryptography, but downstream institutions must reconstruct the same authority facts through bespoke due diligence. That creates repeated integration cost, slower custody/exchange review, weaker machine readability, and more room for maturity claims to be misunderstood.

The intended adoption pressure is therefore interoperability pressure, not protocol coercion.

## No lock-in properties

WS-CAE intentionally does not prescribe a signature scheme, consensus protocol, wallet implementation, custody provider, HSM, KMS, or account architecture.

The reference deployment uses:

- JSON documents;
- a public JSON Schema;
- a Python standard-library CLI;
- deterministic machine-readable output;
- an optional GitHub composite action;
- chain-controlled evidence;
- relying-party-controlled policy.

A chain can stop using the reference implementation and retain the profile semantics independently.

## Relying-party network effect

The consumer-policy layer separates chain facts from consumer requirements.

For example, a chain can truthfully publish `DEVNET + PLUGGABLE_AUTH_ONLY`, while one wallet may accept that for experimental integration and an institutional custodian may require `MAINNET + PQ_MAINNET`. Neither side needs to redefine the chain profile.

This means one published profile can serve many independently chosen policies.

## External alignment

WS-CAE is intended to complement, not replace:

- NIST crypto-agility guidance and NCCoE PQC interoperability/benchmarking work;
- IETF crypto-agility and algorithm-identifier work;
- ISO/TC 307 DLT and wallet interoperability work;
- chain-native rekey, account-abstraction, alias, and programmable-validation mechanisms.

NIST's published crypto-agility guidance calls for environment-specific actionable mechanisms, while its NCCoE migration project explicitly focuses on PQC interoperability and reducing duplicated migration testing. WS-CAE is a digital-asset authority profile aimed at that application-level gap.

## Claims boundary

Adoption does not prove security, post-quantum consensus, standards-body endorsement, certification, or superiority. A profile can expose gaps as readily as strengths.

The adoption proposition is narrower: if a chain already has an authority model that custodians, wallets, auditors, and migration programs need to understand, publishing that state once in a neutral machine-readable form is usually cheaper than making every relying party rediscover it independently.
