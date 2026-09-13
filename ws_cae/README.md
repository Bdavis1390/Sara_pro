# WS-CAE standalone reference package

Version: `0.1.0-research`

WS-CAE is a read-only interoperability profile for comparing digital-asset authority agility across heterogeneous blockchain account models during cryptographic and post-quantum migration.

It is **not** a signature scheme, wallet, consensus protocol, certification program, regulatory standard, or claim that a chain is fully post-quantum secure.

## Why a chain can adopt now

A chain does not need to be PQ-ready. The vocabulary explicitly represents `ROADMAP`, `DRAFT`, `DEVNET`, `TESTNET`, `MAINNET`, `NONE`, and `PLUGGABLE_AUTH_ONLY` states.

The minimum adoption act is one JSON profile. Publishing that profile requires no consensus change, signature change, validator change, wallet migration, SDK dependency, or Worldshepherd runtime.

Start from:

`examples/chain_profile_template.json`

## Why downstream users care

Chain facts and consumer requirements are separate.

A chain publishes one neutral profile. Custodians, exchanges, wallets, treasuries, auditors, insurers, and risk engines can apply their own policy without asking the chain to maintain separate questionnaires.

For example:

```bash
python -m ws_cae.cli ws_cae/examples/reference_pair.json --policy ws_cae/examples/interop_policy.json --pretty
```

The broad interoperability policy accepts the current reference pair. The stricter institutional policy passes Algorand's reference account-authority state while rejecting Ethereum's current DEVNET/pluggable-auth state. That is expected: failure is a machine-readable gap, not a reason a chain cannot publish a truthful profile.

## Reusable CI action

```yaml
- uses: actions/checkout@v4
- uses: Bdavis1390/Sara_pro/.github/actions/ws-cae-conformance@<pinned-commit>
  with:
    profile: path/to/chain-profile.json
    policy: path/to/optional-consumer-policy.json
```

Pin an immutable commit for reproducibility.

The action and CLI have no key-generation, signing, wallet-access, transaction-construction, broadcast, or asset-movement capability.

## Interoperability model

The profile keeps these concepts separate:

- persistent authority identity;
- replaceable authenticator;
- implementation maturity;
- account/vault PQ authorization;
- authorization policy and recovery documentation;
- replay/domain binding and evidence state;
- residual consensus/validator PQ state.

The separation prevents account-level progress from being promoted into a claim of PQ consensus security.

## No-lock-in design

The formats are ordinary JSON and JSON Schema. The reference implementation is Python-standard-library only. Equivalent evidence in another format can satisfy a relying party if that party chooses to accept it.

WS-CAE should be treated as an interoperability vocabulary, not a requirement to run Worldshepherd software.

## Governance and compatibility

This is a `0.x` research package. External users should pin commits. Field meanings must not be silently broadened; material semantic changes require explicit version/change notes. Disagreements should be preserved rather than normalized away.

A future `1.0` candidate should require independent reproduction across multiple ecosystems, external technical review, stable change control, explicit reuse licensing, and at least one independent relying-party implementation.

## Current external-adoption blockers

The main technical review burden is intentionally small in this standalone package. Remaining non-engineering blockers include:

- no external chain adoption yet;
- no independent WS-CAE reproduction yet;
- no standards-body adoption;
- no explicit reuse license currently detected for the repository/package.

The licensing point is material: no license is granted merely by publishing source. Issue #220 tracks the owner/legal/IP decision. A permissive license with explicit patent terms such as Apache-2.0 is a candidate for legal review, not an automatically selected term.

## Claims boundary

Conformance means only that the supplied profile satisfies the published reference rules. Consumer-policy pass means only that the supplied profile satisfies that relying party's selected policy. Neither is certification, compliance, security approval, nor authorization to custody or move assets.
