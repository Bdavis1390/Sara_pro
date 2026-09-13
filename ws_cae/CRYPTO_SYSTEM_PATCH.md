# WS-CAE Crypto System Patch

`WS-CAE-CRYPTO-SYSTEM-PATCH-1` extends the chain patch into an end-to-end cryptocurrency dependency model.

The core rule is deliberately simple:

> A cryptocurrency position is only as migration-ready as its weakest declared critical dependency.

A chain-level PQ result must therefore not be promoted into an end-to-end asset-security claim when a critical issuer, bridge, custody, exchange, wallet, recovery, oracle, rollup, protocol-admin, or consensus dependency remains weaker.

## Component roles

The initial vocabulary supports:

- `CHAIN_AUTHORITY`
- `CONSENSUS_VALIDATOR`
- `ASSET_ISSUER_ADMIN`
- `BRIDGE_MESSAGING`
- `CUSTODY_SIGNING`
- `EXCHANGE_WITHDRAWAL`
- `WALLET_DEVICE`
- `RECOVERY`
- `ORACLE_ADMIN`
- `ROLLUP_PROVER`
- `PROTOCOL_ADMIN`

Not every asset uses every role. A patch should declare only the components that are material to the evaluated ownership or transfer path.

## Readiness states

- `UNASSESSED`
- `CLASSICAL_DEPENDENCY`
- `CRYPTO_AGILE`
- `PQ_PARTIAL`
- `PQ_DEPLOYED`

These are conformance states, not security certifications. `PQ_DEPLOYED` means the declared component has evidence for a deployed PQ state under the author's chosen evidence rules; it does not establish that the implementation is free of defects or that other components are PQ-ready.

## Weakest-link aggregation

Only components marked `critical: true` determine the system state.

The result is one of:

- `SYSTEM_MIGRATION_BLOCKED_BY_CRITICAL_DEPENDENCY`
- `SYSTEM_PARTIAL_PQ_READINESS`
- `ALL_DECLARED_CRITICAL_DEPENDENCIES_PQ_DEPLOYED`
- `CRYPTO_SYSTEM_PATCH_INVALID`

A fully PQ-deployed settlement chain therefore does not cause a stablecoin, bridge, custodial balance, or rollup position to pass if another critical dependency is still classical or unassessed.

## Major reference paths

Synthetic examples are included for:

- native coin / self-custody;
- stablecoin;
- bridged asset;
- exchange-held balance;
- rollup asset.

They are intentionally synthetic and demonstrate semantics only. They do not make claims about the current security of any real cryptocurrency, issuer, bridge, exchange, or wallet.

## Local use

```bash
python -m ws_cae.crypto_system_cli ws_cae/examples/system_stablecoin.json --pretty
```

## Reusable CI action

```yaml
- uses: actions/checkout@v4
- uses: Bdavis1390/Sara_pro/.github/actions/ws-cae-crypto-system@<pinned-commit>
  with:
    patch: path/to/crypto-system.patch.json
```

Pin an immutable commit for reproducibility.

## Execution boundary

The system patch is read-only metadata/conformance tooling. It has no key generation, signing, wallet access, transaction construction, transaction broadcast, custody action, exchange action, bridge action, or asset-movement capability.

## Claims boundary

A system assessment applies only to the dependencies declared in the supplied patch. It is not certification, regulatory compliance, an investment recommendation, a custody approval, a guarantee of quantum resistance, or proof that undeclared dependencies do not exist.
