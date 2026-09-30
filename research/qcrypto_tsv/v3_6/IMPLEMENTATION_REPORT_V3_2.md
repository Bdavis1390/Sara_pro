# Worldshepherd QCRYPTO Bitcoin Hardening — v3.2 Implementation Report

## Objective

Convert the new external-execution evidence into enforceable authorization code, rather than leaving it as a harness result or narrative claim.

## External execution used

The frozen Bitcoin candidate is the same PSBT already accepted by the v3.1 external parser quorum:

- PSBT SHA-256 `b90a18678d229e8961074f2d38fa3debeaec15a46d01925349bbc4cf3dcd26b4`
- txid `259f20588df355fb3732c1fd4f41d5d8666d1bc512dc83c554515cc1b3d1205d`
- input value 100000 sat
- output value 99000 sat
- fee 1000 sat
- parser receipt SHA-256 `d500100cf1e291b2e8eb2d6a0fa89f0b59cb83a4cea0988541b6a02967f3c6cf`

A deterministic external PQ challenge was derived from those exact values, the policy epoch, and the required PQ algorithm set. Its SHA-256 is `e8299f29ebf1bc616fe5a1db6ddf415800eea51d2f637e1746f1d73381ed8c96`.

Supabase Edge then executed:

1. ML-DSA-65 via `@noble/post-quantum@0.7.1`
   - public key 1952 bytes
   - signature 3309 bytes
   - sign/verify true
   - corrupted signature rejected
   - signature SHA-256 `684a5f96b9edf39e8f66ad6c77b2a9567d29bc0c09aee6ed7fc812725ccb1f0b`

2. SLH-DSA-SHA2-128f via `@noble/post-quantum@0.7.1`
   - public key 32 bytes
   - signature 17088 bytes
   - sign/verify true
   - corrupted signature rejected
   - signature SHA-256 `109a5c32fd1c42f2edf9c7bbadaa4a97f7b4d0806e508547e99a109ae8396f2e`

The combined candidate-bound external PQ evidence receipt hashes to `79a124693b6c959ea9e1cf43d8fcd2e4bdf5309b562a502cec793f286fd090d3` under the v3.2 domain-separated receipt hash.

## Code changes

### `external_pq_evidence.py`

Adds a strict validator and deterministic challenge builder. The validator requires:

- exact PSBT SHA-256;
- exact txid and fee;
- exact prior external parser receipt lineage when present;
- exact policy epoch;
- distinct required PQ algorithms;
- only PQ algorithms from the standards registry;
- exact challenge SHA-256;
- PASS execution rows;
- successful sign/verify;
- corrupted-signature rejection;
- signature/public-key sizes matching the standards registry;
- nonempty execution target and implementation library;
- configurable minimum execution-target count;
- optional multi-family diversity.

The receipt is treated as **execution evidence only**, never as a Bitcoin consensus signature, release signature, certification, or HSM/TEE attestation.

### `signing_gate.py`

Adds optional mandatory external PQ evidence. Its canonical receipt SHA-256 and candidate challenge SHA-256 are added to the signing-policy payload. Consequently any change to the external evidence changes the signing-policy hash and final release-intent hash.

### `control_plane.py`

Adds governed policy controls so SARA/PRIME preparation can require the same external evidence. The policy hash now commits to whether external PQ evidence is mandatory, minimum external target count, and family-diversity requirement.

### `crypto_agility.py`

Adds explicit FIPS 205 policy metadata for `SLH-DSA-SHA2-128f` and `SLH-DSA-SHAKE-128f`, both with 17088-byte signatures and 32-byte public keys. This closes a real registry gap exposed by the external execution work.

## Fail-closed tests added

The v3.2 tests cover:

- exact external challenge reproduction;
- actual hosted external PQ receipt validation;
- signing-gate mandatory evidence;
- integrated governed-policy mandatory evidence;
- missing evidence rejection;
- wrong candidate challenge rejection;
- signature-size mismatch rejection;
- failed corruption-control rejection;
- insufficient PQ-family diversity rejection.

Frozen suite target: **132 tests passed, zero failures**.

## Bound candidate result

For the frozen example:

- external parser receipt SHA-256 `d500100cf1e291b2e8eb2d6a0fa89f0b59cb83a4cea0988541b6a02967f3c6cf`
- external PQ evidence receipt SHA-256 `79a124693b6c959ea9e1cf43d8fcd2e4bdf5309b562a502cec793f286fd090d3`
- signing-policy SHA-256 `bce9323f8a34ca3cbe459cb797cb15e3005572508fecb0cc531a384d5492f57e`
- release-intent SHA-256 `8bf6e3c15a60d2e5e28adccf3dd24c174f121c71195402186fe51f10807d2b9f`

## Remaining external gates

- verified Bitcoin Core 31.1 execution on REGTEST/SIGNET in a separately hosted VM;
- live AWS KMS ML-DSA in an authorized AWS account;
- second independently administered external PQ provider/fault domain;
- attributable third-party reproduction receipt;
- future activated Bitcoin consensus PQ path.

No mainnet use, real-value movement, or transaction broadcast is authorized or claimed by this package.
