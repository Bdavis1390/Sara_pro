# WS-SDA G8 — Frozen Adversarial/Fault Corpus V1

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH — EXACT-HEAD CI REQUIRED**
Date: 2026-09-18
Branch: `feature/ws-sda-g8-adversarial-corpus-20260918`
Parent stack: G1 -> G7

## 1. Objective

G8 freezes the first cross-gate adversarial/fault corpus before any G9 10x claim.

The corpus is committed as:

`fixtures/ws_sda_g8_adversarial_corpus_v1.json`

and contains exactly **60 named cases** spanning G1 through G7.

The mandatory false-negative budget is:

```text
0
```

A failed mandatory case blocks the gate. No weighted average can offset it.

## 2. Frozen distribution

- G1 provenance/schema/replay/releasability: 12 cases
- G2 workload + transport identity: 8 cases
- G3 adapter isolation/resource abuse: 8 cases
- G4 CCSDS/version/unit/grammar handling: 8 cases
- G5 hypothesis/conflict handling: 6 cases
- G6 signed human release authorization: 10 cases
- G7 DDIL/rejoin/ECHO/replay: 8 cases

Total: **60**.

One G3 shell-metacharacter case is a positive safety control: the literal argument is
allowed through without shell execution. The G5 outlier case expects explicit
multi-hypothesis retention rather than rejection. The remaining cases require
blocking, rejection, quarantine, conflict surfacing, tamper detection, or explicit
identity separation.

## 3. Security properties under test

The frozen corpus covers, among other cases:

- unknown schema fields;
- malformed/non-finite covariance/state input;
- disabled or mismatched interface contracts;
- backwards/mutated replay;
- stale/releasability quarantine;
- workload signature tamper, revocation, expiry and future issuance;
- source/adapter identity mismatch;
- missing/mismatched mTLS transport identity;
- oversized input, timeout, output floods, bad exit status and invalid adapter path;
- shell-metacharacter non-execution;
- wrong CCSDS versions, units, duplicate fields and unsupported observables;
- cross-object/cross-epoch/cross-frame fusion attempts;
- incompatible state observations retained as multiple hypotheses;
- signed release semantic tampering;
- release replay and use-time expiry;
- DDIL journal capacity and semantic conflicts;
- persistent journal tamper detection;
- rejoin conflicts with no automatic winner;
- ECHO same-origin semantic mutation;
- replay-sequence misuse;
- replica-node ECHO identity separation.

## 4. Evidence contract

The dedicated CI workflow:

`WS-SDA Adversarial Corpus G8`

runs the frozen corpus against the exact commit, creates JUnit evidence, hashes the
manifest, and emits a JSON evidence record containing:

- exact source commit;
- corpus schema;
- corpus SHA-256;
- frozen case count;
- mandatory false-negative budget;
- result.

A PASS means all 60 frozen cases produced their predeclared expected outcome.

## 5. 10x boundary

G8 does **not** establish a 10x improvement.

It establishes the fixed adversarial workload needed to make a later before/after
comparison meaningful.

For attack channels already at zero accepted escapes, G9 must preserve zero as a
non-regression invariant rather than claiming "10x more zero."

For non-zero metrics, G9 may claim 10x only when the frozen candidate result is no
more than 0.10 times the frozen baseline result under the same declared workload and
measurement procedure.

## 6. Claims boundary

A G8 PASS proves only the committed synthetic/reference software cases on the tested
commit.

It does not establish:

- completeness against real-world adversaries;
- red-team or penetration-test equivalence;
- RF/space operational qualification;
- container/kernel escape resistance beyond the tested cases;
- CCSDS full conformance;
- independent replication;
- customer/government authorization, accreditation, or certification.

## 7. Next gate

G9 must freeze a baseline/candidate benchmark protocol and report raw measurements,
sample counts, uncertainty where applicable, zero-invariant results, and each
individual 10x ratio. Any mandatory metric above its threshold blocks an overall 10x
claim.
