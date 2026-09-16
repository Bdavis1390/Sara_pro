# Keylime #1909 — persistent `total_attestation_failures`

Upstream issue: `keylime/keylime#1909`

Reviewed upstream master: `3476366881d7931407154597d88577895f2f818e`

Claims state: **SOURCE-REVIEWED PATCH CANDIDATE / REQUIRES KEYLIME TESTS + ALEMBIC-HEAD VERIFICATION**

## Objective

Add a cumulative verifier metric that answers a question the existing state cannot answer reliably:

> How many attestations has this agent failed over its persisted lifetime, regardless of later recovery?

`consecutive_attestation_failures` is intentionally reset during recovery. `attestation_count` counts successful attestations. Neither is a cumulative failure counter.

The new field should therefore have distinct semantics:

```text
total_attestation_failures = monotonically increasing count of failed attestation evaluations
```

It must not reset when `consecutive_attestation_failures` resets.

## Ownership audit

At the 2026-09-14 UTC review:

- issue #1909 is open;
- no assignee is shown;
- no matching implementation PR was found;
- the only issue comment raises the persistence-vs-memory design question and does not claim implementation.

Before external submission, repeat the ownership check.

## Current-source findings

### 1. The authoritative increment point already exists

`keylime/verification/tpm_engine.py::TPMEngine._process_results()` currently performs the success/failure accounting in one place.

Success:

```python
self.attestation.evaluation = "pass"
self.attestation.agent.attestation_count += 1
```

Failure:

```python
self.attestation.evaluation = "fail"

if self.attestation.agent.consecutive_attestation_failures is None:
    self.attestation.agent.consecutive_attestation_failures = 1
else:
    self.attestation.agent.consecutive_attestation_failures += 1
```

The cumulative counter belongs in the failure branch immediately adjacent to the consecutive counter. This avoids changing retry, authentication-session, push/pull, timeout, or recovery behavior.

Recommended source shape:

```python
self.attestation.agent.total_attestation_failures = (
    self.attestation.agent.total_attestation_failures or 0
) + 1
```

Then retain the existing consecutive-counter logic unchanged.

### 2. Persist it as common verifier agent state

`keylime/models/verifier/verifier_agent.py` defines `attestation_count` in the common metrics section before PUSH-only fields. The cumulative failure counter should live beside it:

```python
cls._field("attestation_count", Integer)
cls._field("total_attestation_failures", Integer)
```

It should not be PUSH-only because attestation failures occur in both pull and push modes.

The legacy SQLAlchemy mirror in `keylime/db/verifier_db.py::VerfierMain` also needs:

```python
total_attestation_failures = Column(Integer)
```

until that legacy representation is retired.

### 3. Initialize new agents explicitly

`keylime/cloud_verifier_tornado.py` initializes new verifier-agent dictionaries with:

```python
"attestation_count": 0,
"last_received_quote": 0,
```

Add:

```python
"total_attestation_failures": 0,
```

This prevents freshly created agents from depending on nullable-database behavior.

### 4. Include it in REST/state serialization

`cloud_verifier_tornado._from_db_obj()` explicitly enumerates persistent response fields and currently includes `attestation_count`.

Add `total_attestation_failures` beside it so external monitoring can consume the metric without scraping event logs.

Current REST documentation from API 2.1 through 2.5 documents `attestation_count`. Maintainers should decide whether the additive field is documented for all maintained API versions or only the newest contract; the implementation should not silently claim a versioning policy.

## Database migration

Existing migration precedents are:

- `bf48e0c4751d_add_attestation_count_column.py`
- `517a2d6b5cd3_add_consecutive_attestation_failures.py`

The most recent migration head visible in the reviewed source is `a59cc9366774_fix_evidence_items_agent_id_length.py`, whose revision is `a59cc9366774`. Code search found no migration whose `down_revision` points to it.

That makes `a59cc9366774` the current **candidate parent**, but an upstream patch must run `alembic heads` immediately before creating the revision. Do not hard-code this parent if the graph has moved.

The issue requests a default of zero and existing rows need deterministic semantics. Preferred migration behavior is:

1. add the integer column with a database-side zero default or otherwise backfill existing rows to zero;
2. make the post-migration value non-null if that matches current Keylime model conventions;
3. verify SQLite, PostgreSQL, MySQL, and MariaDB migration paths used by project CI;
4. provide a downgrade that drops only this column.

Do not infer historical failures from `consecutive_attestation_failures`: that would convert a streak metric into fabricated lifetime history. Existing agents should start the new cumulative metric at zero at migration time unless maintainers explicitly choose a different, evidence-backed migration policy.

## Regression tests

Extend `test/test_tpm_engine.py` so its shared agent fixture starts with:

```python
self.mock_agent.total_attestation_failures = 0
```

Required assertions:

1. one failed pull-mode attestation -> total = 1;
2. one failed push-mode attestation -> total = 1;
3. repeated failures -> total increments once per failed `_process_results()` call;
4. successful attestation -> total unchanged;
5. FAIL -> PASS with auto-recovery allowed -> consecutive may reset, total does not;
6. FAIL -> PASS with auto-recovery blocked -> total remains cumulative;
7. FAIL -> TIMEOUT -> PASS -> no extra failure is invented by the timeout transition;
8. new agent response exposes zero;
9. DB round-trip preserves a non-zero total across verifier restart/reload;
10. migrated pre-existing agent reads zero rather than null;
11. REST response includes the field without changing existing `attestation_count` semantics.

A particularly important invariant is:

```text
attestation_count + total_attestation_failures
```

must only be interpreted as processed pass/fail evaluations if every evaluation path is proven to terminate in exactly one of those two counters. Do not publish that sum as a new metric without separately validating that invariant.

## Failure semantics

Count a failure when Keylime classifies the attestation evaluation as `fail` in `_process_results()`.

Do **not** increment merely because:

- the agent is temporarily unreachable;
- a scheduling timeout fires;
- the verifier process restarts;
- a retry is queued;
- a stale timeout state is cleared.

Those are communication/lifecycle events, not necessarily failed attestations. Keeping the increment at the evaluation branch preserves this distinction.

## Worldshepherd mapping

This is an ECHO/OVERWATCH telemetry-truth improvement.

Recommended normalized state:

```text
attestation.success_total
attestation.failure_total
attestation.failure_consecutive
attestation.last_received_at
attestation.last_success_at
```

`failure_total` is monotonic state suitable for SLO/error-rate deltas; `failure_consecutive` is operational streak state suitable for backoff and immediate health decisions. They must remain separate.

## Submission boundary

No Keylime code or migration has been executed by Worldshepherd for this candidate. Before upstream submission:

- re-check issue/PR ownership;
- run `alembic heads` on the target revision;
- implement the model, legacy DB, initialization, serialization, migration, tests, and applicable REST docs together;
- run Keylime unit/migration CI across supported databases;
- preserve project-required AI-assistance disclosure/sign-off conventions.

Until those gates pass, this remains a source-reviewed patch candidate, not an upstream fix.