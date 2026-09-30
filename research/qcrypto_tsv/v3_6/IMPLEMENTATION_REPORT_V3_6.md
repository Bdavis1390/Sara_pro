# Worldshepherd QCRYPTO + TSV — v3.6 Implementation Report

**Classification:** `NON-PRODUCTION / MULTI-PROVIDER-SOFTWARE-VALIDATED / CLAIMS-CONTROLLED`

## Objective

v3.6 advances v3.5 from synthetic adversarial input validation to restart-survivable state, provider-failover logic, partition failure handling, source-bound calendar evidence, persistent external receipts, and second-provider software verification. It remains a bounded software/evidence package rather than a live securities venue.

## Exact lineage

- integrated v3.5 parent SHA-256: `9b41b15e58898fe9f8fa836b258b13e93e860d20ea2c19e76693bfb3e3948653`
- QCRYPTO v3.2 root SHA-256: `e0c7c968f6d8f31278d677c881d3dea4173452ffd4b8ba07850d70970fc654bc`
- v3.6 resilience-core SHA-256: `b6920cfa2fb8609991b623ceabe61b8b1c0d432cb293a13082fba8eab1977dfa`
- package source-manifest SHA-256: `c549be2fc7e7f29bd10eb4b1253fe911806a03f4ff8654ac947a6e9e3072dad2`

## New executable controls

### Durable cursor state

`tsv/durable_market_state.py` adds atomic restart-survivable source cursors with:

- source/provider/symbol/session identity binding;
- monotonic sequence persistence;
- replay/reorder rejection after process restart;
- sequence-gap and equivocation rejection;
- exact-duplicate idempotence;
- state SHA-256 validation;
- compare-and-swap detection of stale writers;
- atomic temp-write + replace behavior for the local store.

The local store is explicitly a software control, not a trusted timestamp, HSM-backed ledger, or independent attestation.

### Provider failover and partition control

`tsv/provider_resilience.py` adds:

- registered primary/fallback provider routes;
- health-evidence freshness checks;
- failover only to an allowlisted reachable provider;
- fail-closed behavior when no provider is healthy;
- fail-closed behavior on contradictory reachable partition IDs;
- deterministic failover evidence digests.

### Source-bound calendar evidence

The same module adds a calendar-evidence interface with provider allowlisting, session-date binding, publication freshness, payload SHA-256, verification state, and internally coherent open/close hours. Current test evidence is synthetic; no authoritative market-calendar connection is claimed.

### Operational runtime integration

`tsv/operational_runtime.py` now optionally requires provider-resilience and calendar-evidence gates. A failure in either propagates as an explicit runtime failure and forces `DENY`.

### QCRYPTO evidence binding

`tsv_qcrypto_binding.py` now supports binding the v3.6 external resilience bundle and resilience-core digest into the QCRYPTO/TSV integrity lineage.

## Supabase external persistence execution

A JWT-protected external reproducer was deployed to Supabase with a dedicated Postgres cursor and receipt store.

- project ref: `aspmlcdjnbcujsxdhwri`
- function: `qcrypto-tsv-v3-6-resilience-reproducer`
- function ID: `bae89a73-ce6a-4215-ba54-7b37fdd99f7e`
- version: `1`
- JWT verification: enabled
- deployed bundle SHA-256: `01f577e4f008c40aefbc13e7acfe8bc29d1d8844d988f07d69475f024866c516`
- durable store: Supabase Postgres

Two separate function invocations advanced one market stream from sequence 100 / revision 1 to sequence 101 / revision 2. A later invocation attempted sequence 100 and was denied as a durable replay/reorder. The persisted terminal state remained sequence 101 / revision 2 with state SHA-256 `1d6aa86f93ee64bbf9a43390b36d44ab2f28bb08bbaada8dcb8299749d4c92ca`.

External resilience cases: **10**, all with the expected decision.

| Case | Expected/observed | Receipt SHA-256 |
|---|---|---|
| PERSIST_FIRST | ALLOW | `b4058583c53f62fdb9fde755d144e8e161dc75ed45ad6ad72f579d7a4987dc4e` |
| PERSIST_AFTER_RESTART | ALLOW | `c8b78692ea5cc9cb9057379daa3a202ad7df64f3b9d25c387e73787157fc93d3` |
| PERSIST_REPLAY_AFTER_RESTART | DENY | `5166bac412f8d5ddba0e2db401ccfe6d6cb4a8f275b3d2eb1c4b364fbdca84b4` |
| PRIMARY_PARTITION_FALLBACK | ALLOW | `38b7ac70079392de24ac664dd91ce6aad406895a2e9980a3c313602db7734aca` |
| DUAL_PARTITION_CONFLICT | DENY | `d9d33f249338c8b05cfed236512f32ee8b9daa81732b734b4a7cc483e65fd602` |
| NO_HEALTHY_PROVIDER | DENY | `903f4b3162dcef2a2a44fc013a1897ddf46906991b7f49e2d151c71f9b269587` |
| CALENDAR_VALID | ALLOW | `139625b5c380d193e5195e95f8599d042c3abad4127ab60a4e38e912dac4e880` |
| CALENDAR_STALE | DENY | `348b5288bac333aa2392e7836dc77300022c7019d28dc33ed09a8e4d75988069` |
| CALENDAR_WRONG_PROVIDER | DENY | `d09595c034c9a9c15455273fb8a5525448e9aeaf59cdcc6719eb37da1fa26ca7` |
| WRONG_PARENT | DENY | `774123f9cd3c3fcdd26fce46966aa36f7fc6e1e5242bb2b680649c92a4eec53b` |

Supabase external resilience bundle SHA-256: `ebc3b80d92ec8afca9be7c4265811358d41fbfeddd7f016ef5ef04a1fe2732a5`.

## Second external provider validation — Floot

A separate Floot-hosted verifier was added to the existing Worldshepherd Agent Authority Lab. It independently re-computes the resilience bundle hash and checks exact parent/core lineage, source execution metadata, required case decisions, per-case receipt shape, durable terminal state, and negative claims.

- Floot project: `f4163b52-c816-4a49-a6b1-57ae18847861`
- checkpoint: `94c7ec66-3d27-4a35-add1-2fa003f3a84b`
- verifier spec: **1 file passed / 0 failed**
- positive external verification: HTTP 200 / ALLOW
- verification receipt SHA-256: `2a044c101f2e795b2637fe71089e0d75407aa909973fb1a50592545cc8417d6e`
- wrong-parent mutation: DENY, receipt `4a504ffa1dd7a09226cb7e5fe7364289768199572484e43a6c31c5ce5e361f61`
- case-decision mutation: DENY, receipt `8d9378f22b320de1bf52020e4c2d6e972546c54bd0e536ead60ef77acbd5be25`

This is **provider-diverse software validation**, not independently administered review and not third-party certification.

## Verification state

- regression suite: **301 PASS / 0 FAIL**
- source integrity: **PASS**
- Supabase external resilience bundle validation: **ALLOW**
- second-provider Floot validation: **ALLOW**
- integrated synthetic operational authorization: **ALLOW**
- local restart path: first `ALLOW`, after restart `ALLOW`, replay after restart `DENY`
- operational runtime SHA-256: `88bcded73d87f08fa4c70255ed2a940d10daf80f1b6faeee489de620b51c69f9`
- QCRYPTO/TSV binding SHA-256: `3329207a61f05d7061c3a8f940c2e791da8a1d4d02cb7a8a1d384cf22ef89bba`
- final multi-provider evidence binding SHA-256: `c4ccd1edee4fe8ff85f708ff1db6f8acdd827cb3ad0c411ae6e05d3e5cbf9c02`

## Claims boundary

### Established by v3.6

- restart-survivable local cursor control;
- externally persisted Postgres sequence state across separate hosted invocations;
- external replay denial against that persisted state;
- provider failover and partition-conflict software controls;
- source-bound synthetic calendar evidence controls;
- integration into the operational authorization path;
- Supabase external execution plus Floot second-provider verification;
- deterministic hashes tying the evidence together.

### Not established

- licensed SIP or exchange data;
- authoritative market-calendar connectivity;
- qualified/legal issuer delivery;
- production HA/SLA guarantees;
- independently administered validation;
- third-party certification;
- regulatory approval, registration, or legal compliance determination;
- live tokenized-equity trading, custody, clearing, or settlement;
- real-value movement.

## Next gate

The next meaningful gate is provider qualification with **authorized real read-only sandbox/test data** where available, plus independently administered reproduction by a reviewer who controls their own environment and credentials. Live trading is neither required nor authorized for that evidence step.
