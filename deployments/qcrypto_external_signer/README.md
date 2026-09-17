# QCRYPTO external signer / custody trust domain

Status: **REFERENCE CUSTODY-RELEASE SIGNER / NO MAINNET OR BROADCAST AUTHORITY**

This package is deliberately separate from SARA. It independently verifies the frozen
`WS-LIVE-VALUE-EXECUTION-HANDOFF-V1` package, the short-lived ML-DSA-65 human approval,
the unsigned-payload digest, the observed network identity, and its own signer identity.
It then produces a one-use **custody-release attestation**.

The first tranche does **not** create a Bitcoin or Ethereum consensus-native transaction
signature. That distinction is intentional: ML-DSA release authorization can protect the
custody decision without pretending current Bitcoin/Ethereum transaction rules natively
accept ML-DSA signatures.

## Trust separation

The custody process:

- does not import the SARA package or its registry;
- has its own trusted human-approval public-key map;
- has its own signer key/HSM boundary;
- has its own durable one-use ledger;
- independently reconstructs the execution-intent and SARA handoff digests;
- rejects mainnet, transaction broadcast, and chain-native signing requests in this tranche;
- never returns or persists signer private-key bytes.

## Durable state semantics

`INVOKING` is committed before the signer/HSM is called.

- confirmed signer result -> `SIGNED` with a retained receipt;
- exact retry after `SIGNED` -> the retained receipt, no second signer invocation;
- crash/retry observed in `INVOKING` -> `INDETERMINATE`;
- signer/provider exception after invocation begins -> `INDETERMINATE`;
- `INDETERMINATE` -> no automatic retry; human reconciliation is required;
- a human approval ID cannot authorize a second request ID.

This prevents a network timeout or process crash from turning an uncertain signing result
into a duplicate signature attempt.

## Reference networks

The reference policy permits only:

- `BITCOIN / SIGNET`;
- `ETHEREUM / HOODI`;
- `SYNTHETIC / CI`.

Even on Signet/Hoodi the output remains a custody-release attestation. Native transaction
construction/signing/broadcast requires a separate, chain-specific adapter and separate
human authorization.

## Claims boundary

The reference package demonstrates software custody controls only. It does not establish
production HSM/KMS integration, FIPS 140 validation, mainnet authorization, movement of
real value, a native post-quantum Bitcoin/Ethereum transaction signature, or end-to-end
post-quantum security of any cryptocurrency network.
