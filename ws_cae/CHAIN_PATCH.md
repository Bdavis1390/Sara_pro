# WS-CAE Chain Patch

Status: `0.1.0-research`

The WS-CAE Chain Patch is a data-only interoperability layer for publishing a chain's authority-agility and post-quantum migration state in one machine-readable file.

The patch does not alter consensus, transaction validity, validators, signing algorithms, wallets, custody, or chain execution. It describes the current state and binds that description to public evidence.

## Minimum adoption

A chain publishes one file, conventionally:

`ws-cae.patch.json`

The file contains:

- the WS-CAE patch version;
- the chain name;
- one authority profile;
- one or more public evidence references.

The current reference schema is:

`ws_cae/patch.schema.json`

The checker is:

```bash
python -m ws_cae.patch_cli ws-cae.patch.json --pretty
```

A relying party may optionally apply its own policy:

```bash
python -m ws_cae.patch_cli ws-cae.patch.json --policy consumer-policy.json --pretty
```

## Why this is a patch rather than a protocol fork

A chain can publish the patch before it is post-quantum ready. The vocabulary records deployment maturity, account/vault authorization state, protocol commitment, recovery/policy documentation, evidence state, and residual consensus status separately.

This means a chain can truthfully report, for example:

- a mainnet native PQ account path;
- a devnet implementation that is already fork-scheduled;
- a live authority-alias mechanism with future PQ authenticators;
- a constrained mainnet PQ protection path that does not represent network-wide migration.

No one of those states is silently promoted into another.

## Reference patch set

The standalone package includes four examples using the same contract:

- `examples/algorand.patch.json`
- `examples/ethereum.patch.json`
- `examples/sui.patch.json`
- `examples/bitcoin-qsb.patch.json`

They deliberately cover different chain architectures and maturity states.

## CI adoption

A repository can use the reusable action:

```yaml
- uses: actions/checkout@v4
- uses: Bdavis1390/Sara_pro/.github/actions/ws-cae-chain-patch@<pinned-ref>
  with:
    patch: ws-cae.patch.json
```

A consumer policy can be supplied as a second input.

For reproducibility, pin an immutable commit or release tag when one is available.

## Claims boundary

A valid patch means the file is structurally conformant, the embedded authority profile is conformant, the chain/profile identity is consistent, and evidence references satisfy the reference checks.

It does not certify the truth of external evidence, certify a chain as secure, imply post-quantum consensus, establish regulatory compliance, or create standards-body endorsement.

The current package has no explicit reuse license. Issue #220 tracks that owner/legal/IP decision; publication alone does not grant reuse rights.
