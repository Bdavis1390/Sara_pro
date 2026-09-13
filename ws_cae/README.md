# WS-CAE standalone reference package

Version: `0.1.0-research`

WS-CAE is a read-only interoperability profile for comparing digital-asset authority agility across heterogeneous blockchain account models during cryptographic and post-quantum migration.

The package now includes the **WS-CAE Chain Patch**: a one-file, evidence-bound chain status contract that can be adopted without changing consensus, transaction validity, validators, signing algorithms, wallets, SDKs, or custody systems.

It is **not** a signature scheme, wallet, consensus protocol, certification program, regulatory standard, or claim that a chain is fully post-quantum secure.

## One-file chain patch

A chain can publish:

`ws-cae.patch.json`

and validate it with:

```bash
python -m ws_cae.patch_cli ws-cae.patch.json --pretty
```

See `CHAIN_PATCH.md` and the four reference patches for Algorand, Ethereum, Sui, and Bitcoin/QSB.

The patch keeps **deployment maturity** and **protocol commitment** separate. For example, a protocol feature may be implemented on devnet and already scheduled for a future fork without being mislabeled as mainnet-deployed.

## Why a chain can adopt now

A chain does not need to be PQ-ready. The vocabulary represents `ROADMAP`, `DRAFT`, `DEVNET`, `TESTNET`, `MAINNET`, `NONE`, `PLUGGABLE_AUTH_ONLY`, `PQ_MAINNET_LIMITED`, and full `PQ_MAINNET` authorization states.

The minimum adoption act is one JSON profile or one evidence-bound chain patch. Publishing either requires no consensus change, signature change, validator change, wallet migration, SDK dependency, or Worldshepherd runtime.

## Why downstream users care

Chain facts and consumer requirements are separate.

A chain publishes one neutral profile. Custodians, exchanges, wallets, treasuries, auditors, insurers, and risk engines can apply their own policy without asking the chain to maintain separate questionnaires.

For example:

```bash
python -m ws_cae.cli ws_cae/examples/reference_pair.json --policy ws_cae/examples/interop_policy.json --pretty
```

The broad interoperability policy accepts the current reference pair. The stricter institutional policy passes Algorand's reference account-authority state while rejecting Ethereum's current devnet/pluggable-auth state. That is expected: failure is a machine-readable gap, not a reason a chain cannot publish a truthful profile.

## Reusable CI actions

Profile check:

```yaml
- uses: actions/checkout@v4
- uses: Bdavis1390/Sara_pro/.github/actions/ws-cae-conformance@<pinned-commit>
  with:
    profile: path/to/chain-profile.json
    policy: path/to/optional-consumer-policy.json
```

Chain patch check:

```yaml
- uses: actions/checkout@v4
- uses: Bdavis1390/Sara_pro/.github/actions/ws-cae-chain-patch@<pinned-commit>
  with:
    patch: path/to/ws-cae.patch.json
```

Pin an immutable commit for reproducibility.

Both actions are read-only and have no key-generation, signing, wallet-access, transaction-construction, broadcast, or asset-movement capability.

## Interoperability model

The profile keeps these concepts separate:

- persistent authority identity;
- replaceable authenticator;
- implementation maturity;
- protocol/governance commitment state;
- account/vault PQ authorization;
- authorization policy and recovery documentation;
- replay/domain binding and evidence state;
- residual consensus/validator PQ state.

The separation prevents roadmap, governance, account-level, or application-level progress from being promoted into a claim of mainnet or PQ consensus security.

## No-lock-in design

The formats are ordinary JSON and JSON Schema. The reference implementation is Python-standard-library only. Equivalent evidence in another format can satisfy a relying party if that party chooses to accept it.

WS-CAE should be treated as an interoperability vocabulary and chain patch contract, not a requirement to run Worldshepherd software.

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

Conformance means only that the supplied profile or patch satisfies the published reference rules. Consumer-policy pass means only that the supplied profile satisfies that relying party's selected policy. Neither is certification, compliance, security approval, nor authorization to custody or move assets.
