# QCRYPTO public-testnet chain deployment

Status: **HOST-DEPLOYMENT PACKAGE / NO MAINNET AUTHORITY**

This package is the deployable node boundary for the QCRYPTO longevity program.
It deliberately keeps native protocol semantics intact:

- Bitcoin target: **Signet** (`-signet`), preserving Bitcoin's PoW test-chain behavior.
- Ethereum target: **Hoodi**, chain ID **560048**, for validator/staking infrastructure testing.

The package does not contain wallet private keys, validator private keys, seed phrases,
withdrawal credentials, live-value authorization, or a mainnet deployment switch.

## Deployment sequence

1. Provision a persistent Linux host with Docker/Compose.
2. Pin Bitcoin Core, Ethereum execution-client, and Ethereum consensus-client images by immutable SHA-256 digest in `.env`.
3. Generate the Engine API JWT secret **on the deployment host** and store it under `secrets/engine-jwt.hex` with restrictive permissions. This secret authenticates EL/CL Engine API traffic; it is not a wallet/validator key.
4. Render the Compose file and verify that no mainnet flag, wallet key mount, validator key mount, or public admin/RPC port is present.
5. Start the observer nodes.
6. Record chain identity and synchronization evidence:
   - Bitcoin reports chain `signet`.
   - Ethereum execution reports chain ID `560048`.
   - Ethereum consensus client reports network `hoodi` and is connected to the execution client.
7. Run recovery/rollback and restart tests before attaching any external signer.
8. Treat any Bitcoin transaction signing/broadcast or Hoodi validator activation as a separate human-operated change under an external signer/HSM boundary.

## Hard boundaries

QCRYPTO itself does not:

- create/import/export wallet private keys;
- create/import/export validator signing keys;
- sign or broadcast Bitcoin transactions;
- activate an Ethereum validator;
- move value;
- enable Bitcoin or Ethereum mainnet;
- claim that Bitcoin or Ethereum are end-to-end post-quantum secure.

## Evidence needed to promote from HOST_READY to NODE_ONLINE

A deployment receipt must include, at minimum:

- host identifier that does not disclose a private key or credential;
- immutable image digests;
- deployment revision SHA;
- Bitcoin Signet chain identity and best-block height;
- Ethereum Hoodi chain ID and execution head;
- consensus sync/finality status;
- persistent-volume identifiers;
- health-check results;
- restart/rollback result;
- external-signer boundary state;
- explicit `mainnet_permitted=false` and `live_value_authorized=false` claims.

`NODE_ONLINE` is still not validator activation, transaction execution, or post-quantum security proof.
