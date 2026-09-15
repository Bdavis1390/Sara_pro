# Keylime #1941 — push-attestation cadence contract review

Date: 2026-09-12

Claims state: **SOURCE-CONFIRMED CROSS-REPO CONFIGURATION MISMATCH / NOT UPSTREAM ACCEPTED**

Upstream issue: `keylime/keylime#1941`

Related repositories: `keylime/keylime`, `keylime/rust-keylime`

## Executive finding

Issue #1941 is a strong Worldshepherd trust/resilience contribution candidate because the reported cadence mismatch is directly visible in current source in both the Python verifier and Rust push-model agent.

The defect is not merely that one default constant is different. The push model currently has multiple independent concepts that are all being used as if they represented one timing contract:

- verifier steady-state `quote_interval`;
- verifier failure/backoff cap;
- verifier-provided `seconds_to_next_attestation` response metadata;
- Rust agent local fallback `attestation_interval_seconds`;
- timeout detection derived from verifier cadence.

These values diverge when configuration is missing, malformed, or a response cannot be parsed. That can silently turn a roughly 2-second evidence cadence into a 60-second cadence while the system remains operational enough to log only a warning.

No matching open fix PR was found in either `keylime/keylime` or `keylime/rust-keylime` during this review.

## Source confirmation — Python verifier

Current Keylime source reviewed for this record contains these distinct behaviors:

- `push_agent_monitor.py`: `quote_interval` with `fallback=2.0` for timeout scheduling and periodic checks;
- `web/verifier_server.py`: `quote_interval` with `fallback=2.0` for push-agent timeout calculations;
- `cloud_verifier_common.py`: `quote_interval` with `fallback=2.0` for reported attestation period;
- `cloud_verifier_tornado.py`: `quote_interval` with `fallback=2.0` in push monitoring paths;
- `web/verifier/attestation_controller.py`: `quote_interval` with `fallback=60` as the maximum exponential-backoff interval;
- `models/verifier/attestation.py`: `config.getint("verifier", "quote_interval")` with no fallback when calculating the next attestation time.

This creates three different missing-config semantics for the same named option: 2 seconds, 60 seconds, or configuration failure/exception behavior.

## Source confirmation — Rust push agent

Current `rust-keylime` source reviewed for this record shows:

- documented `attestation_interval_seconds = 60` in `keylime-agent.conf`;
- test/default paths returning 60 seconds;
- `StateMachine` stores that configured value as `measurement_interval`;
- on a successful verifier response, `extract_next_attestation_interval()` uses `meta.seconds_to_next_attestation` when present;
- when the response has no `meta`, omits `seconds_to_next_attestation`, or fails JSON parsing, the agent logs a warning and returns `self.measurement_interval`.

Therefore, with default configuration, a malformed or incomplete otherwise-successful verifier response can switch the agent from the verifier-directed cadence to a 60-second local cadence.

## Why simply changing 60 to 2 is not enough

A hard replacement could accidentally collapse distinct policy concepts:

- normal evidence cadence;
- retry/backoff after rejection/failure;
- offline/local fallback cadence when the verifier cannot provide scheduling metadata.

These may legitimately need different defaults.

The underlying issue is that the contract between verifier and agent does not clearly specify which value owns each state and what the fallback hierarchy must be.

## Recommended contract

Worldshepherd recommends defining three explicit timing concepts even if maintainers keep existing configuration names for compatibility.

### 1. Steady-state attestation interval

Authoritative source during normal operation: verifier `quote_interval`, communicated to the agent as `seconds_to_next_attestation`.

### 2. Failure retry/backoff interval

Authoritative source: verifier retry/backoff configuration. It should have an explicit maximum and should not borrow a semantically unrelated fallback accidentally.

### 3. Agent-local fallback interval

Used only when a response cannot provide a valid next interval or the verifier is temporarily unreachable. Its default should be intentionally selected relative to the expected steady-state cadence rather than implicitly inheriting an unrelated historical 60-second value.

## Safer repair options

### Option A — single shared compatibility default

Use the verifier's existing 2-second `quote_interval` default consistently in all Python fallback reads and align the Rust push-agent fallback default to 2 seconds.

Advantage: minimal behavior model.

Risk: a 2-second local retry during prolonged verifier failure may be more aggressive than desired.

### Option B — explicit local fallback configuration

Retain a separately configurable agent fallback but change naming/documentation so users understand it is not the steady-state interval, and choose a safer default derived from or closer to the verifier cadence.

Advantage: separates network/failure behavior from normal evidence cadence.

Risk: wider configuration/API change.

### Option C — bounded adaptive fallback

On successful but malformed verifier responses, reuse the last valid verifier-provided interval for a bounded number/time window before falling back to the local default. On transport failure, use retry/backoff semantics instead.

Advantage: avoids sudden 30x cadence changes from a single malformed response.

Risk: introduces state and more complex recovery semantics.

Worldshepherd preference: **define the semantic contract first, then use the smallest implementation that enforces it**. Option B is the cleanest conceptual model; Option A is the smallest compatibility patch.

## Validation matrix

A cross-repo regression should cover:

| Condition | Expected scheduling source |
| --- | --- |
| valid response with `seconds_to_next_attestation` | verifier-provided value |
| valid response, `meta` missing | explicitly documented local fallback |
| valid response, field missing | explicitly documented local fallback |
| malformed JSON response | explicitly documented local fallback or response error policy |
| verifier rejects evidence | retry/backoff policy, not steady-state cadence |
| verifier unreachable | transport retry policy |
| config file missing `quote_interval` | one consistent verifier default everywhere |
| agent config missing local fallback | one explicit agent default |

Tests must verify both the chosen sleep interval and the warning/error signal so cadence degradation cannot be silent.

## Observability improvement

Expose or log the **reason/source** for the selected next interval, for example:

- `verifier_response`;
- `agent_local_fallback`;
- `failure_backoff`;
- `transport_retry`.

The value alone is insufficient for operators to distinguish intended policy from degraded scheduling.

If metrics exist for push attestation, consider a low-cardinality counter for fallback activation. Do not encode agent IDs or high-cardinality response content in metric labels.

## Worldshepherd contribution decision

**Classification: P1 / CROSS-REPO CONFIGURATION-CONTRACT + REGRESSION CANDIDATE.**

Internal screening score: **92/100**.

This issue is a strong fit for Worldshepherd because it concerns degraded-state truth and recovery semantics rather than a cosmetic default. Before drafting an upstream patch, seek maintainer agreement on whether local fallback cadence is supposed to equal steady-state cadence or remain a distinct policy. Once that is settled, the code change and cross-repo tests are bounded.
