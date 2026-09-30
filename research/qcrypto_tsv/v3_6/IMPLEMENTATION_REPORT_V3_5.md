# Worldshepherd QCRYPTO + SEC TSV — v3.5 Implementation Report

**Classification:** `NON-PRODUCTION / EXTERNAL-SYNTHETIC-ADVERSARIAL-EXECUTED / CLAIMS-CONTROLLED`

## Objective

v3.5 closes the next engineering gap identified in v3.4: market-data source identity and sequencing, freshness/clock-skew controls, conflict/failover semantics, and hash-bound issuer-notice delivery evidence. The work is additive to the exact v3.4 integrated parent; it does not replace the QCRYPTO lineage or relax prior claims boundaries.

## Exact parent lineage

- Integrated v3.4 parent SHA-256: `806db617532dc8840dca3f39504efa4cd78f5b4312005d730e5a73e4b54fffd8`
- QCRYPTO v3.2 root parent SHA-256: `e0c7c968f6d8f31278d677c881d3dea4173452ffd4b8ba07850d70970fc654bc`
- v3.5 market/issuer control-core SHA-256: `4b4e1c85b80b8ad5b9326cbacec0a8754dcc80ec98cf2b2e7bc917cd921d8341`
- v3.5 package source-manifest SHA-256: `1b771236b7fb10dab1ea9162481ffd055172f7b7565a18883ce9eec7067b1ead`

## New software controls

### `tsv/market_data_adapter.py`

Implements a fail-closed market-data ingestion layer with:

- operator-controlled source-kind/source-ID registry binding;
- exact symbol/session binding;
- SHA-256 payload-shape checks;
- verification flag enforcement;
- configurable freshness ceiling;
- future-clock-skew bound;
- effective-to-observed delay bound;
- monotonic sequence enforcement;
- replay/reorder rejection;
- same-sequence/different-payload equivocation rejection;
- sequence-gap rejection;
- effective-time reorder rejection;
- exact duplicate idempotence;
- primary-listing-exchange status requirement;
- fail-closed halt/pause handling;
- cross-source status conflict rejection;
- explicit resume quorum requiring SIP agreement when enabled;
- LULD pause treatment as a **supplemental safeguard**, not as an invented substitute for the SEC primary-exchange-stoppage requirement.

### `tsv/issuer_delivery.py`

Adds hash-bound issuer-notice delivery evidence with:

- symbol and issuer identity binding;
- exact Notice SHA-256 binding;
- allowlisted delivery-channel control;
- provider and receipt identifier requirements;
- provider payload SHA-256 validation;
- delivery/record timestamp ordering;
- provider-record delay ceiling;
- 30-calendar-day wait enforcement;
- fail-closed issuer-objection hold;
- deterministic receipt digest.

The result is explicitly labeled `HASH_BOUND_DELIVERY_EVIDENCE_ONLY_NOT_LEGAL_PROOF_OF_SERVICE`. No qualified-delivery, digital-signature, trusted-timestamp, or legal-service claim is made.

### `tsv/operational_runtime.py`

The operational authorization path can now require both the adversarial market-data adapter and issuer-delivery receipt. Either failing adds an explicit runtime failure (`MARKET_DATA_ADAPTER` or `ISSUER_DELIVERY`) and forces `DENY`.

### `tsv/external_adversarial.py`

Validates the exact hosted v3.5 external evidence bundle, including JWT enforcement, deployed function identity, one positive case, all required negative cases, receipt hashes, parent/control-core binding, and negative-claim preservation.

### `tsv_qcrypto_binding.py`

The QCRYPTO/TSV binding now optionally commits to:

- the v3.5 external adversarial bundle hash; and
- the v3.5 control-core hash.

This makes the new externally executed evidence part of the integrity lineage rather than unbound narrative evidence.

## Hosted external adversarial execution

Target:

- provider: Supabase Edge Functions
- project ref: `aspmlcdjnbcujsxdhwri`
- function: `qcrypto-tsv-v3-5-adversarial-reproducer`
- function ID: `2f1af029-403b-4ce9-912f-d262c613873d`
- version: `1`
- JWT verification: **enabled**
- deployed bundle SHA-256 reported by Supabase: `f8b1c8989888f546723b65696cbaba253c8e3c8d2366add9c8b9c8296aa70bc6`
- source `index.ts` SHA-256: `8ea85e7eeeb83b0e1da31a4c5baa2ad7c7293f6d753da250e6a850bdb5200fbb`

The external reproducer is bound to the exact v3.4 release hash and v3.5 control-core hash. It uses **synthetic** market source IDs (`sim-primary`, `sim-sip`, `sim-luld`) and a synthetic issuer-delivery provider.

### Positive external execution

Request `31` returned HTTP 200 / `ALLOW` with all expected checks passing.

Receipt SHA-256: `0bd3861bd5090fabd2073de65504db113a1bbd71ad4bbbfa795f959a36976a8d`.

### External negative executions

All 11 negative cases returned HTTP 200 / `DENY` on the intended gate:

| Case | Request | Intended failed gate | Receipt SHA-256 |
|---|---:|---|---|
| stale market message | 32 | `MARKET_FRESHNESS_CLOCK` | `6cad7ef1835a426bd6be6a0fc6d139c2ed2ea1bc0ac03d66daa21eb78a5fd1b8` |
| sequence gap | 33 | `MARKET_SEQUENCE_GAP` | `5d07192cd66f27fe2b8d298776a80ef4b9b82651a30f0712cd092f900cbd9934` |
| replay/reorder | 34 | `MARKET_SEQUENCE_REPLAY_OR_REORDER` | `a0f28b5df5ea117809c88548e7c8512060867dfe3f1ce4b7a764117df83be080` |
| sequence equivocation | 35 | `MARKET_SEQUENCE_EQUIVOCATION` | `8ecafbd73a8732a1d3f82a1157e1f0ac26cf913bfb033f889df9185e1b8f4586` |
| cross-source status conflict | 36 | `MARKET_STATUS_CONFLICT` | `786ef1c5b56fe63e79978b3b0e93447352bf2b72cc8ab1bcc317f2ff1f2cdbcd` |
| unregistered source | 37 | `MARKET_SOURCE_IDENTITY` | `97036ef1ae3e98bdab816397a576436ff277fe76123e5f684724f3427ced357a` |
| incomplete resume quorum | 38 | `RESUME_QUORUM` | `d57494798c97929b31f9e1f2b2fec8137a28451d846e2dbac6a3cb416b198680` |
| issuer Notice digest mismatch | 39 | `ISSUER_NOTICE_DIGEST` | `40f2442865d4f5a1e7ecdadc89d988e917574104088bffec498bd05a56990a55` |
| issuer wait too short | 40 | `ISSUER_30_DAY_WAIT` | `209e84893abf59683adfb4a73bf1e25c72d7cd158c198337b0b6ab638809ab9d` |
| issuer objection present | 41 | `ISSUER_OBJECTION_HOLD` | `7807b0cd17d617ca36e3459b7a468a4a463c319d98e3e1eda7368ac2688c2c58` |
| wrong parent hash | 42 | `PARENT_V34_BINDING` | `e18359be8c186ee4b5a942d67df36ab428f13e7e80a8b3e7c25ee4cb0ce97aff` |

Domain-separated external evidence-bundle SHA-256: `551ca894c536219189a554517cf9126e8d168ab19cb96fc5320ee03a2bb79c95`.

## Local verification

- full regression suite: **268 PASS / 0 FAIL**
- source integrity: **PASS**
- external adversarial bundle validation: **ALLOW**
- integrated synthetic operational authorization: **ALLOW**
- operational runtime SHA-256: `1f452a7c65ddffc71a78f10416a8083ee29a2ef0eab20f6677502356a3aa02ef`
- market-data batch SHA-256: `9279ae1c92712d06abd111679f4530a9a848080059cf13a03551c39502a5ba65`
- issuer-delivery receipt SHA-256: `c113a9f08e7fcbfd53d38d7a39b9f03620e0ddfc5551dd375deb0a4b0a1e186f`
- QCRYPTO/TSV binding SHA-256: `c60a12a5a8757370f3a861c55a92dd70b548a515a54bc46024fd66e15c7a45cc`

`ALLOW` in these records means only that the supplied controlled/synthetic inputs satisfy the implemented software checks.

## Claims boundary

### Established by v3.5

- actual source-identity/freshness/sequence/conflict code, not merely a harness description;
- actual issuer-delivery digest/timing/objection code;
- integration of both into the operational authorization path;
- external JWT-protected execution of one positive and 11 adversarial negative cases;
- local validation of the external evidence bundle;
- cryptographic commitment of the v3.5 external evidence and control core into the QCRYPTO/TSV integrity binding;
- 268 regression tests passing in the working tree before release packaging.

### Not established

- licensed SIP data access;
- live primary-listing-exchange or LULD connectivity;
- qualified or legally sufficient issuer proof-of-delivery;
- digital signatures or trusted timestamps on issuer delivery;
- SEC approval, legal compliance, registration, or exemption eligibility for a real operator;
- live tokenized-equity trading;
- production custody, clearing, settlement, broker-dealer, transfer-agent, or exchange/ATS operation;
- real-value movement;
- independent third-party validation/certification.

## Next gate

The next high-value gate is **real-provider adapter qualification without trading**: connect read-only licensed/authorized market-data and delivery-provider sandboxes where legally and contractually permitted, capture independently attributable receipts, exercise outage/failover and clock-drift scenarios, and obtain an independently administered reproduction. No live securities transaction is needed to advance that evidence level.
