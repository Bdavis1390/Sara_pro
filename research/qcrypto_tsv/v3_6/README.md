# Worldshepherd QCRYPTO + SEC TSV — Integrated Candidate v3.5

**Classification:** `NON-PRODUCTION / EXTERNAL-SYNTHETIC-ADVERSARIAL-EXECUTED / CLAIMS-CONTROLLED`

v3.5 adds fail-closed market-data identity/sequence/freshness/conflict controls and hash-bound issuer-delivery evidence to the exact v3.4 integrated parent. It also externally executes one positive and 11 adversarial negative cases on a JWT-protected Supabase Edge reproducer and binds that evidence into the QCRYPTO/TSV integrity lineage.

- Regression suite: **268 PASS / 0 FAIL**
- v3.5 source manifest: `1b771236b7fb10dab1ea9162481ffd055172f7b7565a18883ce9eec7067b1ead`
- v3.5 control core: `4b4e1c85b80b8ad5b9326cbacec0a8754dcc80ec98cf2b2e7bc917cd921d8341`
- external adversarial bundle: `551ca894c536219189a554517cf9126e8d168ab19cb96fc5320ee03a2bb79c95`
- external positive receipt: `0bd3861bd5090fabd2073de65504db113a1bbd71ad4bbbfa795f959a36976a8d`
- QCRYPTO/TSV binding: `c60a12a5a8757370f3a861c55a92dd70b548a515a54bc46024fd66e15c7a45cc`

**Boundary:** the external market and delivery inputs are synthetic. No licensed SIP/exchange/LULD connectivity, qualified delivery attestation, SEC approval, legal compliance, live venue operation, or real-value trading is claimed.

See `IMPLEMENTATION_REPORT_V3_5.md` and `INDEPENDENT_REPRODUCTION_INSTRUCTIONS_V3_5.md`.

---

## Preserved v3.4 and earlier README lineage

# Worldshepherd QCRYPTO + SEC TSV — Integrated Candidate v3.4

**Classification:** `NON-PRODUCTION / EXTERNAL-SOFTWARE-REPRODUCED / CLAIMS-CONTROLLED`

v3.4 binds the existing QCRYPTO v3.2 hardening line and the SEC TSV software-control profile to a JWT-protected hosted external reproducer. The hosted reproducer returned one controlled `ALLOW` case and six intended fail-closed `DENY` cases; the resulting evidence bundle is cryptographically validated and committed into the QCRYPTO/TSV integrity binding.

- Local suite: **221 PASS / 0 FAIL**
- v3.4 source manifest: `a1b27899aa939560389d70e368c872024ab0116aa3d3525e38321fc950d87e21`
- external TSV evidence bundle: `b3773256881b1690587378d651d4d637bdc3c9d581ba204905e4675852d16625`
- hosted positive receipt: `7ef9a0174fe3f429489d258228dc91ca8475a9db7cb43434469aebdd4ec85137`
- QCRYPTO/TSV binding: `75ce1203810359194ef63f10b56ffb745121c794a0c5fc086c03ece0daa096b6`

**Boundary:** these are software-execution and provenance results. They are not SEC approval, legal compliance, a live tokenized-securities venue, licensed market-data connectivity, or independent certification.

See `IMPLEMENTATION_REPORT_V3_4.md` and `INDEPENDENT_REPRODUCTION_INSTRUCTIONS_V3_4.md`.

---

## Preserved parent README (QCRYPTO v3.2)

# Worldshepherd QCRYPTO — Bitcoin Hardening Candidate v3.2

**Classification:** `OUTAGE_DEVELOPMENT_CANDIDATE / RECOVERY_SCAFFOLD / NON-MAINNET`

v3.2 extends v3.1 from external Bitcoin-parser agreement into **candidate-bound external PQ execution evidence that can be made mandatory by the signing gate and the integrated governed control plane**. The package remains an application/custody authorization layer: it is not Bitcoin Core, not a consensus change, not a mainnet signer, not a FIPS module validation claim, and not proof of hardware-enclave protection.

## v3.2 completion

For the frozen SIGNET-style PSBT:

- PSBT SHA-256: `b90a18678d229e8961074f2d38fa3debeaec15a46d01925349bbc4cf3dcd26b4`
- txid: `259f20588df355fb3732c1fd4f41d5d8666d1bc512dc83c554515cc1b3d1205d`
- fee: `1000 sat`
- external parser receipt SHA-256: `d500100cf1e291b2e8eb2d6a0fa89f0b59cb83a4cea0988541b6a02967f3c6cf`

The exact candidate was converted into the deterministic external PQ challenge:

`WS-QCRYPTO-EXTERNAL-PQ-CANDIDATE-V1|<psbt>|<txid>|<fee>|<parser-receipt>|v3.2|ML-DSA-65,SLH-DSA-SHA2-128f`

Challenge SHA-256: `e8299f29ebf1bc616fe5a1db6ddf415800eea51d2f637e1746f1d73381ed8c96`.

Two hosted Supabase Edge executions over that exact challenge passed:

| Algorithm | Library | Signature | Result |
|---|---|---:|---|
| ML-DSA-65 | `@noble/post-quantum@0.7.1` | 3309 bytes | sign/verify PASS; corrupted signature rejected |
| SLH-DSA-SHA2-128f | `@noble/post-quantum@0.7.1` | 17088 bytes | sign/verify PASS; corrupted signature rejected |

The external PQ evidence quorum receipt is canonically rebound as SHA-256 `79a124693b6c959ea9e1cf43d8fcd2e4bdf5309b562a502cec793f286fd090d3`.

## Actual coding fixes in v3.2

- `external_pq_evidence.py` implements strict candidate-bound external PQ evidence validation.
- `crypto_agility.py` now models the FIPS 205 `SLH-DSA-SHA2-128f` and `SLH-DSA-SHAKE-128f` parameter sets rather than treating the fast 128-bit variants as unknown algorithms.
- `prepare_psbt_signing()` can require external PQ execution evidence, exact transaction identity, exact fee, exact parser-receipt lineage, exact policy epoch, exact PQ algorithm set, standard signature/public-key sizes, successful sign/verify, and adversarial corruption rejection.
- The external PQ receipt hash and candidate-challenge hash are committed into the signing-policy hash, and therefore into the final release intent.
- `GovernedSigningPolicy` can require the same external evidence in the integrated SARA/PRIME path rather than leaving it as optional metadata.
- Optional family diversity enforcement requires at least one lattice and one hash-based PQ algorithm family when configured.
- Missing evidence, stale/mismatched challenge binding, wrong fee/txid/PSBT, wrong standard sizes, duplicate/missing algorithms, failed sign/verify, failed corruption rejection, or insufficient execution-target diversity all fail closed.

For the frozen candidate with external parser and external PQ evidence required:

- signing-policy SHA-256: `bce9323f8a34ca3cbe459cb797cb15e3005572508fecb0cc531a384d5492f57e`
- release-intent SHA-256: `8bf6e3c15a60d2e5e28adccf3dd24c174f121c71195402186fe51f10807d2b9f`

See `evidence/EXTERNAL_PQ_CANDIDATE_QUORUM_V1.json` and `evidence/EXTERNAL_PQ_BOUND_PREPARATION_V3_2.json`.

## Existing hardening retained

The v3.x line also retains strict PSBTv0/v2 parsing, UTXO provenance, descriptor/private-key guards, BIP-371/BIP-373 metadata validation, fee and feerate ceilings, exact output intent binding, signature/sighash firewalls, deterministic migration-PSBT construction, durable anti-retry journals, operator quorum, key rotation/anti-rollback, Q-day emergency state, chain-context binding, external dual Bitcoin parser quorum, CBOM/source integrity, and SARA/PRIME/ECHO/OVERWATCH governance.

## Verification

Run:

```bash
python -m unittest discover -s tests -v
python scripts/generate_evidence.py
```

The frozen v3.2 package is expected to pass **132 tests with zero failures** before packaging.

## Claims boundary

### Established

- local application-level ML-DSA-65 and SLH-DSA-SHA2-128s cryptographic execution through OpenSSL where the runtime supports those algorithms;
- hosted external ML-DSA-65 and SLH-DSA-SHA2-128f software execution on Supabase Edge;
- exact candidate challenge binding for those hosted PQ executions;
- two independently implemented hosted Bitcoin PSBT parsers agree on the frozen candidate;
- external parser and external PQ evidence can be mandatory, fail-closed signing-policy inputs.

### Not established

- live Bitcoin Core RPC agreement (scheduled separately on an external VM);
- live AWS KMS ML-DSA execution;
- hardware TEE/HSM attestation;
- independent third-party certification;
- multiple independently administered external PQ fault domains;
- activated Bitcoin consensus post-quantum signatures;
- mainnet authority or transaction broadcast.

---

## v3.3 — SEC TSV control-plane integration

This candidate has been reconciled against exact frozen QCRYPTO v3.2 and WS-TSV v0.3 parent hashes. It adds a bounded software control plane derived from SEC Release 34-106402, including regulatory date/deadline controls, computed affiliate volume limits, transaction transparency validation, operational-event evidence, integrated runtime authorization, and deterministic QCRYPTO/TSV lineage binding.

Frozen local target: **213 tests passed / 0 failed**.

This code is not an SEC determination or legal opinion and is not deployed as a trading venue. External market-data adapters, regulatory communication workflows, public hosting, production custody/settlement, independent validation, and live trading remain outside the established evidence boundary.

## v3.6 — durable resilience and multi-provider software validation

Current integrated continuation adds restart-survivable market cursor state, provider failover/partition controls, source-bound calendar evidence, a Supabase Postgres external persistence reproducer, and a second-provider Floot verifier. Frozen development target: **301 tests passed, zero failures**. The evidence remains synthetic/read-only and non-production; no licensed market feed, live TSV deployment, regulatory approval, or independently administered certification is claimed.
