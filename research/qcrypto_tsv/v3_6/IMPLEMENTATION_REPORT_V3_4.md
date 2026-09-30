# Worldshepherd QCRYPTO + SEC TSV — v3.4 External Execution Integration Report

## Objective

Move the SEC TSV control profile past local-only execution by deploying a narrowly scoped, JWT-protected external software reproducer, executing one controlled positive case plus six fail-closed adversarial cases, validating the resulting evidence bundle locally, and binding that bundle into the QCRYPTO/TSV provenance chain.

This does **not** establish an SEC compliance determination, legal opinion, registered venue, live market-data connection, production deployment, or independent certification.

## Exact parent lineage

- QCRYPTO v3.2 parent ZIP SHA-256: `e0c7c968f6d8f31278d677c881d3dea4173452ffd4b8ba07850d70970fc654bc`
- TSV v0.3 parent ZIP SHA-256: `7c1ee785f82c5180a7920d8d34889698b3367680788aa4d80b80ed51a1babefe`
- Integrated v3.3 parent release SHA-256: `fab44ddd5a1d46516f8d2b9fc759f4f23db7d811ab8a7d7a9b79da2d0400a25f`
- v3.3 source-manifest SHA-256: `36af6e42fb78ab6e97a56678b87afc02ff71d4ea79d3d11a778eb03a31c9becc`

## External execution target

The external reproducer was deployed to the existing Worldshepherd QCRYPTO Supabase project:

- project ref: `aspmlcdjnbcujsxdhwri`
- function: `qcrypto-tsv-v3-3-external-reproducer`
- function ID: `8ce128d5-cf6b-4ec2-ad83-0c6393443ef7`
- function version: `1`
- JWT verification: **enabled**
- deployed function bundle SHA-256 reported by Supabase: `a20ef60d231e2cd1afe7cc471bc40d033344684a7b428f2a054d7197f2e9e425`

The function is a test reproducer bound to the exact v3.3 release and source manifest. It does not connect to licensed SIP, LULD, primary-exchange, issuer, broker, custodian, clearing, or settlement infrastructure.

## Hosted positive execution

Supabase request `18` returned HTTP 200 / `ALLOW` for the controlled synthetic input. All 12 external checks passed:

1. exact release binding;
2. exact source-manifest binding;
3. modeled exemption window;
4. initial public Notice 30-calendar-day lead time;
5. operations-start window;
6. initial SEC notice one-business-day check under the explicitly non-authoritative weekends-only reproducer calendar;
7. issuer 30-calendar-day wait;
8. affiliate volume threshold;
9. transaction-transparency feed posture;
10. transaction required fields;
11. 10-minute publication bound;
12. structured significant-operational-event evidence.

Hosted pass receipt SHA-256: `7ef9a0174fe3f429489d258228dc91ca8475a9db7cb43434469aebdd4ec85137`.

The synthetic Tier-1 aggregate share was `0.0001`, below the modeled `0.0025` threshold.

## Hosted fail-closed executions

Six independently submitted negative cases all returned HTTP 200 / `DENY` for the intended gate:

| Case | Request | Intended failed gate | Receipt SHA-256 |
|---|---:|---|---|
| Exemption expired | 19 | `EXEMPTION_WINDOW` | `e8025e8d1cbddbc52adf878f0c59a74ca0f0b5cc5db600ad0a6f1d0c9ec0f881` |
| Initial Notice too late | 20 | `INITIAL_PUBLIC_NOTICE_30_CALENDAR_DAYS` | `e28a5c2b532ad934d630be3c880961c259780cfd199954ed14e49b0943bfe0bf` |
| Operational-event SEC notice missing | 21 | `SIGNIFICANT_OPERATIONAL_EVENT_EVIDENCE` | `4c5f14546120569b06b5edb00339a88f3df2c73719e519f9b645391ace39c629` |
| Transaction publication >10 minutes | 22 | `TRANSACTION_PUBLICATION_10_MINUTES` | `4972757f156f2af5271dd1314fc86ae1d30e80feabc44e304d25dcf42b5f021a` |
| Tier-1 aggregate share exceeded | 23 | `AFFILIATE_VOLUME_THRESHOLD` | `c07b62e6006535cc279fb9190c822789d38a1a75a9881b2c2232dc880479b40b` |
| Wrong release binding | 24 | `RELEASE_BINDING` | `5488d89e260f92ba372cb3eeb1749980093bef69f36712f2627bd3181d31e812` |

## New production-oriented code in v3.4

### `tsv/external_execution.py`

Adds a strict local validator for the hosted execution bundle. It requires:

- correct schema and domain-separated bundle hash;
- exact v3.3 parent release and source-manifest lineage;
- expected Supabase execution identity;
- JWT verification enabled;
- deployed function bundle hash shape;
- positive case HTTP 200 / ALLOW;
- all required positive control IDs;
- all six named negative cases;
- each negative case HTTP 200 / DENY on the expected control;
- valid receipt hashes;
- explicit non-claim flags remaining false.

Mutation of the evidence bundle fails closed.

### `tsv_qcrypto_binding.py`

The QCRYPTO/TSV binding can now commit to `external_tsv_execution_bundle_sha256`, so hosted TSV execution evidence changes the final integrity binding rather than remaining unbound narrative evidence.

External execution bundle SHA-256: `b3773256881b1690587378d651d4d637bdc3c9d581ba204905e4675852d16625`.

## Local verification after integration

- regression suite: **221 PASS / 0 FAIL**
- source integrity: **PASS**
- v3.4 source-manifest SHA-256: `a1b27899aa939560389d70e368c872024ab0116aa3d3525e38321fc950d87e21`
- external execution bundle validation: **ALLOW**
- controlled local operational replay: **ALLOW**
- local operational runtime SHA-256: `b125db6342970ca6aff28c6e25f9db6343eee59e4ac0f2aa10fe31cd9a24a0b5`
- QCRYPTO/TSV binding SHA-256: `75ce1203810359194ef63f10b56ffb745121c794a0c5fc086c03ece0daa096b6`

`ALLOW` above means only that the specific synthetic/reproduction inputs satisfy the implemented software checks. It is not a compliance verdict.

## Claims boundary

### Established by this work

- exact-parent integration of QCRYPTO v3.2 + TSV v0.3 through v3.3;
- external deployment of a JWT-protected TSV test reproducer;
- one external positive execution over the frozen v3.3 lineage;
- six external fail-closed adversarial executions;
- local cryptographic validation of the external execution bundle;
- binding of external TSV execution evidence into the local QCRYPTO/TSV integrity chain;
- 221 local regression tests passing after integration.

### Not established

- SEC approval, registration, endorsement, or legal compliance;
- a registered exchange, ATS, broker-dealer, transfer agent, clearing agency, or custodian;
- live tokenized-equity trading;
- licensed SIP, LULD, primary-listing-exchange, or issuer-notice feeds;
- production clearing or settlement;
- real-value movement or mainnet/broadcast authorization;
- authoritative Federal/business-day calendar treatment;
- independent third-party validation or certification.

## Next engineering gate

1. Introduce explicit market-data adapter interfaces with source identity, sequence/freshness, clock-skew, and failover semantics.
2. Inject stale, duplicate, reordered, contradictory, and unavailable-source evidence and require deterministic fail-closed behavior.
3. Bind issuer-notice proof-of-delivery and revised-Notice receipts to ECHO evidence.
4. Add independent reproduction on a separately administered fault domain.
5. Only after those gates, evaluate any real deployment against the actual legal entity, venue architecture, registrations/exemptions, contracts, market-data licenses, custody/settlement model, and counsel review.
